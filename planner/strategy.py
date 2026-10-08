"""Immutable, append-only state/action maps shared by sibling policies."""
from collections.abc import Mapping


class Strategy(Mapping):
    __slots__ = ("parent", "state", "action", "base", "size", "depth")

    def __init__(self, base=None, parent=None, state=None, action=None):
        self.parent = parent
        self.state = state
        self.action = action
        self.base = dict(base or {}) if parent is None else None
        self.size = len(self.base) if parent is None else parent.size + 1
        self.depth = 0 if parent is None else parent.depth + 1

    def extend(self, state, action):
        # Search extends only states currently pending (no existing assignment).
        return Strategy(parent=self, state=state, action=action)

    def get(self, state, default=None):
        node = self
        while node.parent is not None:
            if node.state == state:
                return node.action
            node = node.parent
        return node.base.get(state, default)

    def __getitem__(self, state):
        missing = object()
        value = self.get(state, missing)
        if value is missing:
            raise KeyError(state)
        return value

    def __len__(self):
        return self.size

    def items(self):
        nodes = []
        node = self
        while node.parent is not None:
            nodes.append(node)
            node = node.parent
        yield from node.base.items()
        for node in reversed(nodes):
            yield node.state, node.action

    def __iter__(self):
        for state, _ in self.items():
            yield state

    def copy(self):
        return self  # Immutable: sibling updates create new nodes.

    def __eq__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        if len(self) != len(other):
            return False
        if isinstance(other, Strategy) and self.parent is not None and self.parent is other.parent:
            return self.state == other.state and self.action == other.action
        return dict(self.items()) == dict(other.items())
