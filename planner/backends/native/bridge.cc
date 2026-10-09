// BOAND* bridge to the pinned GPL-3.0-or-later Fast Downward release.
// All calls hold the GIL; task registries and state IDs are capsule-local.
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "evaluation_context.h"
#include "heuristics/max_heuristic.h"
#include "heuristics/lm_cut_heuristic.h"
#include "heuristics/lm_cut_landmarks.h"
#include "per_state_information.h"
#include "state_registry.h"
#include "tasks/root_task.h"
#include "task_utils/successor_generator.h"
#include "task_utils/task_properties.h"
#include <limits>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace {
constexpr const char *CAPSULE = "boand.downward.task";
struct NativeTask {
    std::shared_ptr<AbstractTask> task;
    TaskProxy proxy;
    StateRegistry registry;
    PerStateInformation<int> identifiers{-1};
    std::vector<StateID> states;
    std::unique_ptr<Heuristic> heuristic;
    explicit NativeTask(std::shared_ptr<AbstractTask> task_, const std::string &kind)
        : task(std::move(task_)), proxy(*task), registry(proxy) {
        if (task_properties::has_axioms(proxy) || task_properties::has_conditional_effects(proxy))
            throw std::invalid_argument("Native prototype requires unconditional STRIPS without axioms");
        if (!task_properties::is_unit_cost(proxy))
            throw std::invalid_argument("BOAND* prototype requires unit-cost operators");
        if (kind == "hmax")
            heuristic = std::make_unique<max_heuristic::HSPMaxHeuristic>(task,
                tasks::AxiomHandlingType::APPROXIMATE_NEGATIVE_CYCLES, false,
                "BOAND hmax", utils::Verbosity::SILENT);
        else if (kind == "lmcut")
            heuristic = std::make_unique<lm_cut_heuristic::LandmarkCutHeuristic>(task,
                true, true, false, "BOAND lmcut", utils::Verbosity::SILENT);
        else
            throw std::invalid_argument("Unknown heuristic");
        intern(registry.get_initial_state());
    }
    int intern(const State &state) {
        int &id = identifiers[state];
        if (id == -1) {
            id = static_cast<int>(states.size());
            states.push_back(state.get_id());
        }
        return id;
    }
    State state(int id) {
        if (id < 0 || static_cast<size_t>(id) >= states.size())
            throw std::out_of_range("Invalid state ID for this task");
        return registry.lookup_state(states[id]);
    }
};
void destroy(PyObject *capsule) {
    delete static_cast<NativeTask *>(PyCapsule_GetPointer(capsule, CAPSULE));
}
PyObject *load(PyObject *, PyObject *args) {
    const char *sas, *kind;
    if (!PyArg_ParseTuple(args, "ss", &sas, &kind)) return nullptr;
    try {
        std::istringstream stream(sas);
        tasks::g_root_task.reset();
        tasks::read_root_task(stream);
        auto task = std::move(tasks::g_root_task);
        auto native = std::make_unique<NativeTask>(std::move(task), kind);
        PyObject *capsule = PyCapsule_New(native.get(), CAPSULE, destroy);
        if (capsule) native.release();
        return capsule;
    } catch (const std::exception &error) {
        tasks::g_root_task.reset();
        PyErr_SetString(PyExc_ValueError, error.what());
        return nullptr;
    }
}
template<typename Func> PyObject *with_state(PyObject *args, Func function) {
    PyObject *capsule;
    int id;
    if (!PyArg_ParseTuple(args, "Oi", &capsule, &id)) return nullptr;
    auto *task = static_cast<NativeTask *>(PyCapsule_GetPointer(capsule, CAPSULE));
    if (!task) return nullptr;
    try { return function(*task, task->state(id)); }
    catch (const std::exception &error) {
        PyErr_SetString(PyExc_ValueError, error.what());
        return nullptr;
    }
}
PyObject *successors(PyObject *, PyObject *args) {
    return with_state(args, [](NativeTask &task, const State &state) {
        std::vector<OperatorID> applicable;
        successor_generator::g_successor_generators[task.proxy].generate_applicable_ops(state, applicable);
        PyObject *result = PyList_New(applicable.size());
        if (!result) return static_cast<PyObject *>(nullptr);
        size_t position = 0;
        for (OperatorID id : applicable) {
            auto op = task.proxy.get_operators()[id];
            int child = task.intern(task.registry.get_successor_state(state, op));
            PyObject *pair = Py_BuildValue("ii", op.get_id(), child);
            if (!pair) { Py_DECREF(result); return static_cast<PyObject *>(nullptr); }
            PyList_SET_ITEM(result, position++, pair);
        }
        return result;
    });
}
PyObject *facts(PyObject *, PyObject *args) {
    return with_state(args, [](NativeTask &, const State &state) {
        PyObject *result = PyList_New(0);
        if (!result) return static_cast<PyObject *>(nullptr);
        for (FactProxy fact : state) {
            if (fact.get_value() == 1) {
                PyObject *item = PyLong_FromLong(fact.get_variable().get_id());
                if (!item || PyList_Append(result, item) < 0) {
                    Py_XDECREF(item); Py_DECREF(result); return static_cast<PyObject *>(nullptr);
                }
                Py_DECREF(item);
            }
        }
        return result;
    });
}
PyObject *goal(PyObject *, PyObject *args) {
    return with_state(args, [](NativeTask &task, const State &state) {
        return PyBool_FromLong(task_properties::is_goal_state(task.proxy, state));
    });
}
PyObject *evaluate(PyObject *, PyObject *args) {
    return with_state(args, [](NativeTask &task, const State &state) {
        EvaluationContext context(state);
        int value = context.get_evaluator_value_or_infinity(task.heuristic.get());
        return value == std::numeric_limits<int>::max()
            ? PyFloat_FromDouble(std::numeric_limits<double>::infinity()) : PyLong_FromLong(value);
    });
}
PyMethodDef methods[] = {
    {"load", load, METH_VARARGS, "Load a unit-cost boolean SAS task."},
    {"successors", successors, METH_VARARGS, "Applicable operator IDs and successor IDs."},
    {"facts", facts, METH_VARARGS, "True boolean variable IDs."},
    {"goal", goal, METH_VARARGS, "Test the goal."},
    {"evaluate", evaluate, METH_VARARGS, "Evaluate the selected heuristic."},
    {nullptr, nullptr, 0, nullptr}
};
PyModuleDef module = {PyModuleDef_HEAD_INIT, "_downward_native", nullptr, -1, methods,
                      nullptr, nullptr, nullptr, nullptr};
}
PyMODINIT_FUNC PyInit__downward_native() { return PyModule_Create(&module); }
