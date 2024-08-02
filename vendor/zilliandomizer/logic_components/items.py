from dataclasses import dataclass

""" codes - first byte of item data structure in rom """
KEYWORD = 0x0A
RESCUE = 0x2A
NORMAL = 0x26
MAIN = 0x0D


@dataclass(eq=True, frozen=True)
class Item:
    name: str
    """ for display """
    debug_name: str
    """ human readable unique identifier """
    is_progression: bool
    """ this item can open up new areas in the game """
    required: bool
    """ this item can be required to win (never_exclude in AP api) """
    multiworld: bool
    """ this item should be randomized to other worlds in a multiworld """
    code: int
    """ first byte in rom item data structure (not unique) """
    # Archipelago uses `code` property, so I might want to rename this
    id: int
    """ sixth byte in rom item data structure (not unique) """

    def __hash__(self) -> int:
        return (self.code * 16) | self.id


items = [
    Item("Key Word", "keyword_0", True, False, False, KEYWORD, 0x00),
    Item("Key Word", "keyword_1", True, False, False, KEYWORD, 0x01),
    Item("Key Word", "keyword_2", True, False, False, KEYWORD, 0x02),
    Item("Key Word", "keyword_3", True, False, False, KEYWORD, 0x03),
    Item("Empty", "empty", False, False, True, NORMAL, 0x04),
    Item("ID Card", "card", False, False, True, NORMAL, 0x05),
    Item("Red ID Card", "red", False, True, True, NORMAL, 0x06),
    Item("Floppy Disk", "floppy", False, True, True, NORMAL, 0x07),
    Item("Bread", "bread", False, False, False, NORMAL, 0x08),
    Item("Opa-Opa", "opa", True, True, True, NORMAL, 0x09),
    Item("Zillion", "gun", True, True, True, NORMAL, 0x0A),
    Item("Scope", "scope", False, False, True, NORMAL, 0x0B),

    # rescue
    Item("Apple", "rescue_0", True, True, True, RESCUE, 0x00),
    Item("Champ", "rescue_1", True, True, True, RESCUE, 0x01),
]

MAIN_ITEM = Item("Main Computer", "main", False, True, False, MAIN, 0x00)

item_name_to_item = {
    item.debug_name: item
    for item in items
}
item_name_to_item[MAIN_ITEM.debug_name] = MAIN_ITEM


def _make_item_id(item: Item) -> int:
    return (item.code << 8) | (item.id)


item_name_to_id = {
    item.debug_name: _make_item_id(item)
    for item in items
}
item_name_to_id[MAIN_ITEM.debug_name] = _make_item_id(MAIN_ITEM)

id_to_item = {
    _id: item_name_to_item[item_name]
    for item_name, _id in item_name_to_id.items()
}
