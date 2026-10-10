"""Replay exported PRP rules against original PDDL, without either grounder."""
import argparse
from collections import deque
from functools import lru_cache
import itertools
import json
from pathlib import Path
import re
import resource
from pddl import parse_domain, parse_problem
from pddl.logic.base import And, Not, Or, OneOf
from pddl.logic.effects import AndEffect, When
from pddl.logic.predicates import Predicate, EqualTo
from pddl.logic.terms import Variable
from planner.policy import CYCLE_COST


def ground(predicate, binding):
    return (predicate.name.lower(), tuple((binding[t.name] if isinstance(t, Variable) else t.name).lower() for t in predicate.terms))


def changed_predicates(effect):
    if isinstance(effect, Predicate):return {effect.name.lower()}
    if isinstance(effect, Not):return changed_predicates(effect.argument)
    if isinstance(effect, When):return changed_predicates(effect.effect)
    if isinstance(effect, (AndEffect, And, OneOf)):
        return set().union(*(changed_predicates(e) for e in effect.operands))
    raise ValueError(f'Unsupported PDDL effect: {effect}')


def rules(file, prefix):
    result=[]
    if not file.exists():return result
    for conditions, action in re.findall(r'If holds:([^\n]*)\n'+prefix+r': ([^\n]*)',file.read_text()):
        result.append((tuple((v,int(n)) for v,n in re.findall(r'(var\d+):(\d+)',conditions)),action.split(' / ')[0]))
    return result


class OriginalTask:
    def __init__(self, domain, problem, folder):
        self.domain=parse_domain(str(domain));self.problem=parse_problem(str(problem))
        if self.domain.derived_predicates:raise ValueError('Derived predicates unsupported by independent replay')
        self.actions={a.name.lower():a for a in self.domain.actions}
        dynamic=set().union(*(changed_predicates(a.effect) for a in self.domain.actions))
        facts={ground(f,{}) for f in self.problem.init if isinstance(f,Predicate)}
        if len(facts)!=len(self.problem.init):raise ValueError('Nonpositive initial facts unsupported')
        self.static=frozenset(f for f in facts if f[0] not in dynamic)
        self.initial=frozenset(f for f in facts if f[0] in dynamic)
        self.policy=rules(folder/'policy.out','Execute');self.fsaps=rules(folder/'policy.fsap','Forbid')
        # Forbidden actions form a union, so duplicate rules and their order do
        # not matter. Check a shared required literal once before scanning the
        # rest of its group; a false guard excludes every rule in that group.
        self.fsap_groups={}
        for clauses,name in dict.fromkeys(self.fsaps):
            guard=clauses[:1]
            self.fsap_groups.setdefault(guard,[]).append((clauses[1:],name))
        if not self.policy:raise ValueError('No exported policy rules')
        self.values={}
        # Policy variable indices refer to the PREPROCESSED task, not output.sas.
        for name,values in re.findall(r'begin_variable\n(var\d+)\n-?\d+\n\d+\n(.*?)\nend_variable',(folder/'output').read_text(),re.S):
            parsed=[]
            for value in values.splitlines():
                m=re.fullmatch(r'(Atom|NegatedAtom) ([^(]+)\(([^)]*)\)',value)
                if m:parsed.append((m[1]=='Atom',(m[2],tuple(t.strip() for t in m[3].split(',') if t.strip()))))
                elif value=='<none of those>':parsed.append(None)
                else:raise ValueError(f'Unsupported translated atom: {value}')
            self.values[name]=parsed

    def holds(self, formula, state, binding):
        if isinstance(formula,Predicate):
            fact=ground(formula,binding);return fact in state or fact in self.static
        if isinstance(formula,Not):return not self.holds(formula.argument,state,binding)
        if isinstance(formula,And):return all(self.holds(f,state,binding) for f in formula.operands)
        if isinstance(formula,Or):return any(self.holds(f,state,binding) for f in formula.operands)
        if isinstance(formula,EqualTo):
            term=lambda t:(binding[t.name] if isinstance(t,Variable) else t.name).lower()
            return term(formula.left)==term(formula.right)
        raise ValueError(f'Unsupported condition: {formula}')

    def effects(self, formula, state, binding):
        if isinstance(formula,Predicate):return [(frozenset({ground(formula,binding)}),frozenset())]
        if isinstance(formula,Not):return [(frozenset(),frozenset({ground(formula.argument,binding)}))]
        if isinstance(formula,When):return self.effects(formula.effect,state,binding) if self.holds(formula.condition,state,binding) else [(frozenset(),frozenset())]
        if isinstance(formula,OneOf):return [x for f in formula.operands for x in self.effects(f,state,binding)]
        if isinstance(formula,(AndEffect,And)):
            return [(frozenset().union(*(x[0] for x in xs)),frozenset().union(*(x[1] for x in xs))) for xs in itertools.product(*(self.effects(f,state,binding) for f in formula.operands))]
        raise ValueError(f'Unsupported effect: {formula}')

    def condition(self, clauses, state):
        for variable,index in clauses:
            values=self.values[variable];literal=values[index]
            if literal is None:
                if any(((fact in state or fact in self.static)==positive) for item in values if item is not None for positive,fact in [item]):return False
            else:
                positive,fact=literal
                if (fact in state or fact in self.static)!=positive:return False
        return True

    @lru_cache(maxsize=65536)
    def bound_action(self, name):
        tokens=name.split();action=self.actions[tokens[0]]
        if len(tokens)-1!=len(action.parameters):raise ValueError(f'Action arity: {name}')
        return action,dict(zip((p.name for p in action.parameters),tokens[1:]))

    def successors(self,state):
        selected=[name for clauses,name in self.policy if self.condition(clauses,state)]
        # Exported rules are sorted SC-first, distance, step id (PRP comparator).
        # PRP enables return_if_possible after repairs; emulate its fallback.
        forbidden={name for guard,items in self.fsap_groups.items() if self.condition(guard,state)
                   for clauses,name in items if self.condition(clauses,state)}
        name=next((name for name in selected if name not in forbidden),next(iter(selected),None))
        if name is None or name=='goal':raise ValueError('Reachable nongoal has no action')
        action,binding=self.bound_action(name)
        if not self.holds(action.precondition,state,binding):raise ValueError(f'Inapplicable action: {name}')
        return [(state-deletes)|adds for adds,deletes in self.effects(action.effect,state,binding)]


def replay(domain,problem,folder):
    task=OriginalTask(domain,problem,Path(folder));states=[task.initial];index={task.initial:0};edges=[];goals=[];distance=[0]
    for state in states:
        parent=index[state]
        if task.holds(task.problem.goal,state,{}):goals.append(parent);edges.append([]);continue
        children=[]
        for successor in task.successors(state):
            if successor not in index:index[successor]=len(states);states.append(successor);distance.append(distance[parent]+1)
            children.append(index[successor])
        edges.append(list(set(children)))
    reverse=[[] for _ in states];indegree=[0]*len(states)
    for parent,children in enumerate(edges):
        for child in children:reverse[child].append(parent);indegree[child]+=1
    seen=set(goals);pending=deque(goals)
    while pending:
        for parent in reverse[pending.popleft()]:
            if parent not in seen:seen.add(parent);pending.append(parent)
    if len(seen)!=len(states):raise ValueError('Reachable state cannot reach a goal')
    best=min(distance[g] for g in goals);longest=[0]*len(states);pending=deque(i for i,n in enumerate(indegree) if n==0);visited=0
    while pending:
        parent=pending.popleft();visited+=1
        for child in edges[parent]:
            longest[child]=max(longest[child],longest[parent]+1);indegree[child]-=1
            if not indegree[child]:pending.append(child)
    worst=max(longest[g] for g in goals) if visited==len(states) else CYCLE_COST
    return {'status':'valid','best':best,'worst':worst,'cyclic':visited!=len(states),'reachable_states':len(states),'policy_rules':len(task.policy),'reachable_non_goal_states':len(states)-len(goals),'replay_peak_rss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main():
    p=argparse.ArgumentParser();p.add_argument('request',type=Path);p.add_argument('output',type=Path);args=p.parse_args();request=json.loads(args.request.read_text())
    resource.setrlimit(resource.RLIMIT_AS,(request.get('memory_kb',6000000)*1024,)*2)
    try:result=replay(request['domain_path'],request['problem_path'],request['folder'])
    except ValueError as e:result={'status':'invalid','error':str(e)}
    except Exception as e:result={'status':'validation_error','error':f'{type(e).__name__}: {e}'}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    if result['status']!='valid':raise SystemExit(1)

if __name__=='__main__':main()
