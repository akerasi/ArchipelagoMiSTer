"""
1087d table
00 95d - black space (black room?)
blue    red     paperclip
30 bbe  01 96d  50 d1f - double vertical walls
31 bce  02 97d  51 d2f - right wall (blue dark dots at bottom)
32 bde  03 98d  52 d3f - left wall (blue dark dots at bottom)
        04 99d         - right solid wall red bg (different height offset in bg?)
        05 9ad         - left solid wall red bg (different height offset in bg?)
33 bee  06 9bd  53 d4f - right wall - black solid at top (bddab)
34 bfe  07 9cd  54 d5f - left wall - black solid at top (bddab)
        08 9dd         - right solid wall red bg (black at top, darker bg)
        09 9ed         - left solid wall red bg (black at top, darker bg)
36 c1e  0a 9fd  55 d6f - left wall up from floor
35 c0e  0b a0d  56 d7f - right wall up from floor
        0c a1d         - left wall up from floor (red darker bg?)
        0d a2d         - right solid wall above floor (darker bg?)
39 c4e  0e a3d  59 daf - empty space (red little dark at top, bddab)
        0f a4d         -   red space (lighter at top)
3a c5e  10 a5d  5a dbf - empty space (black solid at top)
        11 a6d         - red space (black solid at top - darker bg)
3b c6e  12 a7d  5b dcf - floor (red darker at top)
        13 a8d         - floor with (red lighter at top)
3c c7e  14 a9d  5c ddf - floor with black solid at top
        15 aad         - floor with red (darker) bg - black solid at top
3d c8e  16 abd  5d def - right moving walkway floor (doesn't move me without some other data, blue not moving)
3e c9e  17 acd  5e dff - left unmoving walkway floor (blue other direction)
40 cbe  18 add  60 e1f - vertical scope in empty space with black solid at top
41 cce  19 aed  61 e2f - vertical scope up from floor
3f cae  1a afd  5f e0f - vertical scope in empty space (red dark row - unused in vanilla)
# red and blue horizontals are 1 tile below top of block, paperclip horizontals are top of block
42 cde  1b b0d  62 e3f - horiz scope in empty space
        1c b1d         - horiz scope in red space (darker bg?)
43 cee  1d b2d  63 e4f - horiz scope above floor
38 c3e  1e b3d  58 d9f - left wall up from floor with black solid top  (confirm blue looks a little buggy)
37 c2e  1f b4d  57 d8f - right wall up from floor with black solid top
        20 b5d         - left wall up from floor with black solid top (darker bg)
        21 b6d         - right wall up from floor with black solid top (darker bg)
        22 b7d         - horiz scope above floor (darker bg)
44 cfe  23 b8d  64 e5f - platform and then black solid at top
45 d0e  24 b9d  65 e6f - platform and then black solid at top above floor
        25 bad         - floor with black solid at top (TODO: how diff from other above?)
                66 e7f - black space with floor
                67 e8f - more black space (probably meant to be used instead of index 0?)
                68 e9f - top left of door to main computer
                69 eaf - top right of door to main computer
                6a ebf - bot left of door to main comp
                6b ecf - bot right
                6c edf - unmovable black space (guessing right wall of black room)
46-4f d1e  26-2f bbd - ? something with elevator? single 0 byte, blank space in table?
"""


# was going to use IntEnum, but I just want them to be seen as int
class Tile:
    # ceiling
    b_ceiling = 0x3a
    p_ceiling = 0x5a
    r_light_ceiling = 0x10
    r_dark_ceiling = 0x11

    b_ceiling_v = 0x40
    p_ceiling_v = 0x60
    r_light_ceiling_v = 0x18

    # space
    b_space = 0x39
    p_space = 0x59
    r_light_space = 0x0e
    r_dark_space = 0x0f

    b_space_v = 0x3f
    p_space_v = 0x5f
    r_dark_space_v = 0x1a

    b_space_h = 0x42
    r_light_space_h = 0x1b
    r_dark_space_h = 0x1c
    p_space_h = 0x62

    # floor
    b_floor = 0x3b
    r_light_floor = 0x12
    r_dark_floor = 0x13
    p_floor = 0x5b

    b_floor_v = 0x41
    r_dark_floor_v = 0x19
    p_floor_v = 0x61

    b_floor_h = 0x43
    r_light_floor_h = 0x1d
    r_dark_floor_h = 0x22
    p_floor_h = 0x63

    # double vertical walls
    b_walls = 0x30
    r_walls = 0x01
    p_walls = 0x50

    # floor and ceiling in same tile
    b_floor_ceiling = 0x3c
    r_light_floor_ceiling = 0x14
    r_dark_floor_ceiling = 0x15
    p_floor_ceiling = 0x5c

    # moving walkways
    b_right_walkway = 0x3d
    b_left_walkway = 0x3e
    r_right_walkway = 0x16
    r_left_walkway = 0x17
    p_right_walkway = 0x5d
    p_left_walkway = 0x5e
