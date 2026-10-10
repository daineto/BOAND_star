"""Compiled no-op actions retain their meaning and parse with Pyperplan."""
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest

from pddl import parse_domain, parse_problem
from pyperplan.pddl.lisp_parser import parse_nested_list
from pyperplan.pddl.parser import Parser

from planner.preprocessing import explicit_empty_effects, get_alloutcome_determinization


DOMAIN = """(define (domain example)
  (:requirements :strips)
  (:predicates (ready) (done))
  ; Mentioning :effect in a comment must not hide the missing clause.
  (:action wait :parameters () :precondition (and (ready)))
  (:action finish :parameters () :precondition (and (ready))
    :effect (and (done) (not (ready)))))
"""


class EmptyEffectTests(unittest.TestCase):
    def test_missing_effect_is_empty_and_other_sections_are_preserved(self):
        normalized = explicit_empty_effects(DOMAIN)
        original = parse_nested_list(StringIO(DOMAIN))
        parsed = parse_nested_list(StringIO(normalized))
        original_wait = next(section for section in original if isinstance(section, list) and section[:2] == [":action", "wait"])
        actual_wait = next(section for section in parsed if isinstance(section, list) and section[:2] == [":action", "wait"])
        self.assertEqual(actual_wait, original_wait + [":effect", ["and"]])
        self.assertEqual([section for section in original if section is not original_wait],
                         [section for section in parsed if section is not actual_wait])
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "domain.pddl"
            file.write_text(normalized)
            domain = Parser(str(file)).parse_domain()
            self.assertFalse(domain.actions["wait"].effect.addlist)
            self.assertFalse(domain.actions["wait"].effect.dellist)
            self.assertTrue(domain.actions["finish"].effect.addlist)
            self.assertTrue(domain.actions["finish"].effect.dellist)

    def test_complete_domain_is_returned_byte_for_byte(self):
        complete = DOMAIN.replace(":precondition (and (ready)))", ":precondition (and (ready)) :effect (and))")
        self.assertEqual(explicit_empty_effects(complete), complete)
        self.assertEqual(explicit_empty_effects(explicit_empty_effects(DOMAIN)), explicit_empty_effects(DOMAIN))

    def test_tireworld_preprocessing_retains_grounded_noop(self):
        root = Path(__file__).resolve().parents[1]
        domain = parse_domain(str(root / "benchmarks/icaps2025/tireworld/domain.pddl"))
        problem = parse_problem(str(root / "benchmarks/icaps2025/tireworld/p01.pddl"))
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            try:
                os.chdir(temporary)
                task = get_alloutcome_determinization(domain, problem)
            finally:
                os.chdir(previous)
        noop = next(op for op in task.operators if "changetire_detdup_1" in op.name)
        self.assertFalse(noop.add_effects)
        self.assertFalse(noop.del_effects)
        self.assertTrue(task.goals)


if __name__ == "__main__":
    unittest.main()
