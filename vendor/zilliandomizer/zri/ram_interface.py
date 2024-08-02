import abc
from dataclasses import dataclass
from typing import ClassVar, Iterable, List, Tuple

from zilliandomizer.zri.ram_ranges import RANGE_READS as _RANGE_READS


@dataclass
class RamData:
    """
    `RamInterface.read` can be implemented like this:

    ```
    data: List[bytes] = []
    for start, end in RamData.RANGE_READS:
        # read this range of ram
        these_bytes = ...
        # If a read is unsuccessful, its range should be empty bytes.
        if failed:
            these_bytes = b''
        data.append(these_bytes)
    return RamData(data)
    ```
    """

    RANGE_READS: ClassVar[Iterable[Tuple[int, int]]] = _RANGE_READS
    """
    This tells you what ranges of ram are needed,
    with a start address and end address (last + 1)
    for each range.

    ( (start, end), (start, end), ... )
    """

    data: List[bytes]
    """
    Each range of ram goes in here.

    If a read is unsuccessful, its range should be empty bytes `b''`

    `len(data) == len(RANGE_READS)`
    """


class RamInterface(abc.ABC):

    @abc.abstractmethod
    async def write(self, addr: int, b: Iterable[int]) -> None:
        """ starting at ram address `addr`, write bytes `b` """
        ...

    @abc.abstractmethod
    async def read(self) -> RamData:
        """ see documentation of `RamData` """
        ...

    @abc.abstractmethod
    def close(self) -> None:
        """ in case some socket needs to be closed or something """
        ...
