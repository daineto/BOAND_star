"""Compact immutable child strategies; materialize an active policy once."""
from collections.abc import Mapping


class Strategy(Mapping):
    __slots__ = ("base", "state", "action")

    def __init__(self, base, state, action):
        # The search never modifies a parent's strategy after creating children.
        self.base = base
        self.state = state
        self.action = action

    def get(self, state, default=None):
        return self.action if state == self.state else self.base.get(state, default)

    def __getitem__(self, state):
        return self.action if state == self.state else self.base[state]

    def __len__(self):
        return len(self.base) + 1

    def __iter__(self):
        yield from self.base
        yield self.state

    def items(self):
        yield from self.base.items()
        yield self.state, self.action

    def materialize(self):
        strategy = self.base.materialize() if isinstance(self.base, Strategy) else self.base.copy()
        strategy[self.state] = self.action
        return strategy

    def copy(self):
        return self

    def __eq__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        if len(self) != len(other):
            return False
        if isinstance(other, Strategy) and self.base is other.base:
            return self.state == other.state and self.action == other.action
        return self.materialize() == dict(other.items())
