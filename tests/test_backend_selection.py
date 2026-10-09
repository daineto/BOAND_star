"""Selection contracts: lazy grounding and explicit backend failures."""
import unittest
from unittest.mock import Mock, patch

from planner.backends import get_backend
from planner.cli import main
from planner.search import boand_star


class BackendSelectionTests(unittest.TestCase):
    def test_grounding_dispatch_is_lazy_and_preserves_failures(self):
        legacy = Mock(return_value='legacy task')
        for name in ('pyperplan', 'downward-strips'):
            with patch('planner.backends.import_module') as imported:
                self.assertEqual(get_backend(name).ground('d', 'p', legacy), 'legacy task')
                imported.assert_not_called()
        for name, factory in [('downward-grounded', 'get_downward_determinization'),
                              ('downward-direct', 'get_direct_determinization')]:
            module = Mock()
            getattr(module, factory).return_value = name
            with patch('planner.backends.import_module', return_value=module):
                self.assertEqual(get_backend(name).ground('d', 'p', legacy), name)
                getattr(module, factory).assert_called_once_with('d', 'p')
                getattr(module, factory).side_effect = RuntimeError('unsupported input')
                with self.assertRaisesRegex(RuntimeError, 'unsupported input'):
                    get_backend(name).ground('d', 'p', legacy)

    def test_unknown_backend_fails_before_parsing(self):
        with patch('planner.search.parse_domain') as parse:
            with self.assertRaisesRegex(ValueError, 'Unknown backend'):
                boand_star('d', 'p', '/unused', backend='typo')
            parse.assert_not_called()

    def test_standalone_cli_preserves_default_and_explicit_selection(self):
        for flags, expected in [([], 'pyperplan'), (['--backend', 'downward-direct'], 'downward-direct')]:
            args = ['planner', 'd.pddl', 'p.pddl', '/out', *flags]
            with patch('planner.cli.boand_star') as search:
                main(args, len(args))
                self.assertEqual(search.call_args.kwargs['backend'], expected)
