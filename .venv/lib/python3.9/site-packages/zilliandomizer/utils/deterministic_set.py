from typing import Dict, Iterable, Iterator, List, Literal, MutableSet, Optional, TypeVar, Union, overload

_T = TypeVar('_T')


class DetSet(MutableSet[_T]):
    """ python set is not deterministic """
    _set: Dict[_T, Literal[True]]

    def __init__(self, iterable: Optional[Iterable[_T]] = None) -> None:
        if iterable is None:
            self._set = {}
        else:
            self._set = {v: True for v in iterable}

    def add(self, value: _T) -> None:
        self._set[value] = True

    def discard(self, value: _T) -> None:
        if value in self._set:
            del self._set[value]

    def __contains__(self, v: object) -> bool:
        return v in self._set

    def __iter__(self) -> Iterator[_T]:
        yield from self._set.keys()

    def __len__(self) -> int:
        return len(self._set)

    @overload
    def __getitem__(self, index: int) -> _T: ...
    @overload
    def __getitem__(self, index: slice) -> List[_T]: ...

    def __getitem__(self, index: Union[int, slice]) -> Union[_T, List[_T]]:
        return list(self._set.keys())[index]

    def copy(self) -> "DetSet[_T]":
        return DetSet(self._set.keys())
