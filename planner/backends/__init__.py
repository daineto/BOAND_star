"""Backend selection shared by search and experiment provenance.

Imports stay lazy so selecting the direct path does not load Unified Planning.
"""
from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class Backend:
    native: bool = False
    grounder: str | None = None
    negative_conditions: str | None = None

    @property
    def uses_translator(self):
        return self.grounder is not None

    def ground(self, domain, problem, legacy_grounder):
        if self.grounder is None:
            return legacy_grounder(domain, problem)
        return getattr(import_module('.grounding', __name__), self.grounder)(domain, problem)


BACKENDS = {
    'pyperplan': Backend(),
    'downward-strips': Backend(native=True),
    'downward-grounded': Backend(native=True, grounder='get_downward_determinization'),
    'downward-direct': Backend(native=True, grounder='get_direct_determinization',
                               negative_conditions='boand-dual-rail-v1'),
}


def get_backend(name):
    try:
        return BACKENDS[name]
    except KeyError:
        raise ValueError(f'Unknown backend: {name}; choose from {", ".join(BACKENDS)}') from None
