from typing import Dict, Generic, TypeVar

_T = TypeVar('_T')


class DisjointSet(Generic[_T]):
    _parents: Dict[_T, _T]

    def __init__(self) -> None:
        self._parents = {}

    def find(self, item: _T) -> _T:
        """
        returns the root item associated with `item`
        """
        if item not in self._parents:
            self._parents[item] = item

        while item != self._parents[item]:
            self._parents[item] = self._parents[self._parents[item]]
            item = self._parents[item]
        return item

    def union(self, a: _T, b: _T) -> None:
        """
        merge `a` and `b` into 1 set
        """
        parent_a = self.find(a)
        parent_b = self.find(b)
        if parent_a != parent_b:
            self._parents[parent_a] = parent_b
