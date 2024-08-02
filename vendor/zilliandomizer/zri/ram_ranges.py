from typing import Literal, Tuple

from zilliandomizer.low_resources import ram_info, rom_info

RangeName = Literal["basic", "new_ram", "door_can"]

assert ram_info.item_pickup_record == 0xc2d0, "moving item_pickup_record invalidates ram range reads"


RANGE_READS: Tuple[Tuple[int, int], ...] = (
    # basic
    (
        ram_info.current_scene_c11f,
        ram_info.map_current_index_c198 + 1
    ),
    # new ram and computer state
    (
        ram_info.computer_state_c280,
        ram_info.opas_c2ee + 1
    ),
    # doors and canisters
    (
        ram_info.door_state_d600,
        ram_info.canister_state_d700 + rom_info.CANISTER_ROOM_COUNT * 2
    )
)
""" (first address, last address + 1) """
