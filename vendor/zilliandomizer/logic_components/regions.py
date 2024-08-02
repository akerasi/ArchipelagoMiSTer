from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Any
# some changes here for working on region connections
# from typing_extensions import Unpack  # type: ignore

from zilliandomizer.logic_components.locations import Location, LocationData, Req  # , ReqArgs


class Region:
    name: str
    door: int
    connections: Dict["Region", Req]
    locations: List[Location]
    computer: bytes
    """ `0xff` for all non-generated rooms """

    def __init__(self, name: str, door: int = 0) -> None:
        self.name = name
        self.door = door
        self.connections = {}
        self.locations = []
        self.computer = b'\xff'

    # this is good for type checking when working with region connections
    # but it doesn't run (I think it's Python 3.11 or something...)
    # def to(self, other: "Region", **req_args: Unpack[ReqArgs]) -> None:
    def to(self, other: "Region", **req_args: Any) -> None:
        """
        make a connection

        if `door` argument `is True`, this connection requires the door of `self` to be open

        both directions, same requirements for the return direction
        """
        if req_args.get("door") is True:
            req_args["door"] = self.door
        self.connections[other] = Req(**req_args)
        other.connections[self] = Req(**req_args)  # Is it bad that I'm not making a deep copy of the union?


@dataclass
class RegionData:
    """ just what's needed for output, serializable """
    name: str
    door: int
    locations: List[LocationData]
    computer: bytes

    @staticmethod
    def from_region(region: Region) -> RegionData:
        return RegionData(
            region.name,
            region.door,
            [LocationData.from_location(loc) for loc in region.locations],
            region.computer
        )

    def to_jsonable(self) -> Dict[str, Any]:
        dct = asdict(self)
        dct["computer"] = list(self.computer)
        return dct

    @staticmethod
    def from_jsonable(dct: Dict[str, Any]) -> RegionData:
        rd = RegionData(**dct)
        rd.locations = [LocationData.from_jsonable(loc) for loc in dct["locations"]]
        rd.computer = bytes(rd.computer)
        return rd
