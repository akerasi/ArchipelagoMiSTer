CANISTER_ROOM_COUNT = 74
""" how many rooms have canisters in them """

bank_7_free_space_1ffdb = 0x1ffdb
""" from here to the end looks like free space """
free_space_end_7e00 = 0x7e00
""" before this is about 200 bytes of space that looks available """
bank_6_free_space_end_b5e6 = 0xb5e6
""" if i disable spoiling demos, i get the bonus of lots of extra free space in bank 6 """
bank_6_second_demo_control_b14a = 0xb14a
""" beginning of control data for second demo """
bank_5_free_space_end_bfdf = 0xbfdf
""" lots of space in bank 5 filled with 0xff """
bank_5_free_space_begin_b8c4 = 0xb8c4

checksum_7ffa = 0x7ffa
"""
The checksum is stored at 0x7FFA, 2 bytes, little endian,
and is the sum of all bytes from 0x0000-0x7FEF and 0x8000-0x1FFFF.
"""
# Thanks to CaitSith2 for the checksum info

load_blue_code_10a3 = 0x10a3
""" code that is run when entering blue area to load tiles into vram """
load_red_code_10cd = 0x10cd
""" code that is run when entering red area to load tiles into vram """

# memory address of tile data when bank 7 is active
blue_basic_banked_tiles_81fd = 0x81fd
apple_rescue_banked_tiles_8695 = 0x8695
champ_rescue_banked_tiles_8b93 = 0x8b93

floppy_display_compare_1899 = 0x1899
"""
max number of floppies displayed on pause screen + 1
```
if floppy_count >= (floppy_display_compare):
    display (floppy_display_change) floppies
```
"""
floppy_display_change_189d = 0x189d
"""
max number of floppies displayed on pause screen
```
if floppy_count >= (floppy_display_compare):
    display (floppy_display_change) floppies
```
"""

floppy_req_instruction_4fb0 = 0x4fb0
""" the conditional jump instruction that checks for the correct number of floppies """

floppy_req_4faf = 0x4faf
""" the number of floppies required at main computer """

floppy_req_13ef = 0x13ef
""" the number of floppies required at ship to win """

floppy_intro_text_1a771 = 0x1a771
""" the text in the introduction that tells how many floppies are required """

tutorial_menu_default_1d0c = 0x1d0c
""" the default cursor position for showing the computer codes in the intro """

current_char_init_0b03 = 0x0b03
""" initialization of which character is currently playing """

char_init_7b98 = 0x7b98
""" initialization of char stats (to ram c150) """

intro_rescue_text_address = 0x1a83b
""" introduction text telling who is captured """
intro_rescue_text = b'CHAMP AND APPLE ARE'

apple_rescue_code_4bdb = 0x4bdb
""" low byte of pointer to ram character stats for whom to rescue when rescuing apple """
champ_rescue_code_4be1 = 0x4be1
""" low byte of pointer to ram character stats for whom to rescue when rescuing champ """

apple_rescue_lines_1add8 = [
    0x1add8,
    0x1ade8,
    0x1adf7,
    0x1ae08,
    0x1ae1d,
    0x1ae28,
]
""" each line of text displayed when rescuing apple """
champ_rescue_lines_1ae38 = [
    0x1ae38,
    0x1ae41,
    0x1ae4e,
    0x1ae5c,
    0x1ae6d,
    0x1ae78,
    0x1ae89,
]
""" each line of text displayed when rescuing champ """

room_table_91c2 = 0x91c2
""" table that contains the rom address for the item data for each map block """

item_pickup_jump_table_4abc = 0x4abc
""" table to jump to code based on the id of the item I'm picking up """

level_up_code_4adf = 0x4adf
""" code to increment level when picking up opa-opa """
level_up_code_plus_4aeb = 0x4aeb
""" relative jump location in level up code """

stats_per_level_table_7cc8 = 0x7cc8
""" table with the stats that are determined by level """

increment_gun_code_4af8 = 0x4af8
""" code to increment gun level """
code_after_increment_gun_7c1e = 0x7c1e
""" code to run after incrementing gun level """

increment_scope_code_4b07 = 0x4b07
""" code to acquire scope """

terrain_index_13725 = 0x13725
"""
starting at `_DATA_13725_` is 65 bytes for each of the 17 rows

each row is 8 bytes for each column
    - 00 `00` scrolling hallway - `01` non-scrolling hallway - `03` room
    - 01-02 banked address of terrain data for that location
    - 03 unknown
    - 04 map index (0-135)
    - 05-06 banked address of door data (bank 4 (this one) - add 0x8000)
    - 07 unknown

followed by 1 byte at the end of the row 0xfe
"""
terrain_begin_10ef0 = 0x10ef0
"""
The terrain data is packed tightly with some run-length encoding:

command, byte, ...
```
if command & 0x80:
    command & 0x7f is the number of bytes to take
else:
    command is the number of copies of the next byte
```
Each room's terrain data ends with `0x00`
"""
terrain_end_120da = 0x120da
""" the byte after the last room's 0x00 """
door_data_begin_13ce8 = 0x13ce8
""" the beginning of the data containing the doors in each room """

continue_count_init_0af5 = 0x0af5
""" the initialization value for the number of continues (+ 1) """
continue_dec_addr_2523 = 0x2523
""" the address of the code that decrements the continues """
continue_dec_code = [0x35, 0xfa, 0x1a, 0x25]
""" the code that decrements the continues """

demo_inc = 0x0bca
""" the location of the instruction that increments which demo is played next """

game_over_code_retry_24c2 = 0x24c2
""" the game over code when the player chooses "retry" """
game_over_code_0_continues_251a = 0x251a
""" the game over code when there are 0 continues left """
game_over_code = [0x3e, 0x00, 0x32]
""" the first bytes of the vanilla code for game over """

base_explosion_scene_210b = 0x210b
""" the scene that the base explosion leads to """
base_explosion_jump_2112 = 0x2112
""" the parameter of the jump instruction in the base explosion """

base_explosion_timer_init_207b = 0x207b
""" 2 bytes bcd value of base explosion timer (0x00, 0x03) """
base_explosion_timer_text_6044 = 0x6044
""" 3 bytes of text for base explosion timer """

zillion_men_1ae99_1af22 = (0x1ae99, 0x1af22)
""" the two places that say '"zillion" men' """

font_tiles = {
    chr(ord('A') + i): 0x14110 + (i * 0x10)
    for i in range(26)
}
""" the graphic tile data for each character that can be displayed """
font_tiles[' '] = 0x14000
# TODO: find tiles for punctuation and digits

np_sprites_80b6 = 0x80b6
"""
2 bytes for each map index, pointer to data for non-player sprites in each room

at each pointer location:
1 byte for the number of sprites in this room,
then 6 bytes for each sprite

rr rr xx yy tt tt

rr rr: ram address where this sprite goes
xx: x coord in room
yy: y coord in room
tt tt: type of thing

```
09 00, 0c 00 unknown outside
0e 00 ship entrance
10 00 hallway elevator
34 0x hallway bread
39 80 shoot trigger to open door (room 0d)
32 00 mine    y a8 is where y 98 canister sits
14 00-03 enemy
37 00-03 falling enemy
21 ss auto gun
   22 down, moving
   23 right, moving
   24 left, moving
   38 down, not moving
   3a right, not moving
   3b left, not moving
1f ss barrier
   00 horizontal length 1
   01 horizontal length 2
   02 vertical   length 1
   03 vertical   length 1 + small tile (unused?)
   04 vertical   length 2
   05 vertical   length 2 + small tile
   06 horizontal length 1.5
   07 vertical   length 2 - small tile
```
"""

init_splice_address_0ac3 = 0x0ac3
""" a call to a subroutine in the initialization of a new game """
init_splice_target_2e7d = 0x2e7d
""" a subroutine called in the initialization of a new game """
refill_card_injection_address_1389 = 0x1389
""" 8 bytes of code at ship refill to give a card if you have none """

alarmed_enemy_entrance_table_7f04 = 0x7f04
""" 1 byte for each map index, indexes to data for alarmed enemy entrances """
alarmed_enemy_entrance_data_7f86 = 0x7f86
"""
6 bytes for each alarmed enemy entrance
1st entry is null (00, 00, 00, 00, 00, 00)

x, y, x velocity?, ff if falling?, enemy type, 12 from left - 13 from right - 11 from ceiling
"""

startup_splice_26e5 = 0x26e5
"""
address of call instruction when game is booting up

bank is set to 5 before this call instruction
"""

save_hallway_bread_4714 = 0x4714
""" `ld (hl), a` (machine code 0x77) saves information that hallway bread was picked up """
