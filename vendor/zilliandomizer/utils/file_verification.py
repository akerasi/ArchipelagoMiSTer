""" what the rom needs to pass unit tests """

from .verified import verified, v_door_data

from zilliandomizer.options import ID, chars, char_to_jump
from zilliandomizer.low_resources import asm, ram_info, rom_info


def set_verified_bytes(b: bytearray) -> None:
    # floppy display
    b[rom_info.floppy_display_compare_1899] = 0x06
    b[rom_info.floppy_display_change_189d] = 0x05

    # floppy req code
    b[rom_info.floppy_req_instruction_4fb0] = 0xc2
    # floppy req
    b[rom_info.floppy_req_4faf] = 0x05
    b[rom_info.floppy_req_13ef] = 0x05

    # floppy intro text
    floppy_text = b'THE 5 FLOPPY DISKS FROM'
    for i, char in enumerate(floppy_text):
        b[rom_info.floppy_intro_text_1a771 + i] = char

    # bank 5 free space
    for a in range(rom_info.bank_5_free_space_begin_b8c4 + 0xc000,
                   rom_info.bank_5_free_space_end_bfdf + 0xc001):
        b[a] = 0xff

    # rescue sprite code
    for a in range(rom_info.bank_7_free_space_1ffdb, len(b)):
        b[a] = 0xff
    b[rom_info.load_blue_code_10a3 + 0] = asm.LDHL
    b[rom_info.load_blue_code_10a3 + 1] = 0xfd
    b[rom_info.load_blue_code_10a3 + 2] = 0x81
    b[rom_info.load_red_code_10cd + 0] = asm.LDHL
    b[rom_info.load_red_code_10cd + 1] = 0x95
    b[rom_info.load_red_code_10cd + 2] = 0x86

    # tutorial
    b[rom_info.tutorial_menu_default_1d0c] = 0x4c

    # rescue states
    b[rom_info.char_init_7b98] = 0x01
    b[rom_info.char_init_7b98 + 16] = 0x00
    b[rom_info.char_init_7b98 + 32] = 0x00
    b[rom_info.apple_rescue_code_4bdb] = 0x70
    b[rom_info.champ_rescue_code_4be1] = 0x60

    # rescue text
    apple_text = [
        b'THANK YOU FOR',
        b'RESCUING ME:',
        b'I<M SORRY THAT',
        b'I WAS CAPTURED:',
        b'IS CHAMP',
        b'ALL RIGHT;',
    ]
    for line_i, line in enumerate(apple_text):
        for char_i in range(len(line)):
            b[rom_info.apple_rescue_lines_1add8[line_i] + char_i] = line[char_i]
    champ_text = [
        b'YOU<RE',
        b'VERY LATE:',
        b'WHAT<VE YOU',
        b'BEEN DOING;',
        b'AH> I<VE',
        b'BUNGLED THINGS',
        b'BADLY:',
    ]
    for line_i, line in enumerate(champ_text):
        for char_i, char in enumerate(line):
            b[rom_info.champ_rescue_lines_1ae38[line_i] + char_i] = char

    # introduction captured text
    for i in range(len(rom_info.intro_rescue_text)):
        b[rom_info.intro_rescue_text_address + i] = rom_info.intro_rescue_text[i]

    # gun and level code block
    for i in range(rom_info.free_space_end_7e00 - 216, rom_info.free_space_end_7e00):
        b[i] = 0xff

    # opa pickup
    pickup_jump_table_entry = rom_info.item_pickup_jump_table_4abc + 2 * ID.opa
    b[pickup_jump_table_entry] = rom_info.level_up_code_4adf % 256
    b[pickup_jump_table_entry + 1] = rom_info.level_up_code_4adf // 256

    # gun data
    init_table_gun = rom_info.char_init_7b98 + 6  # gun in initialization of char data
    b[init_table_gun] = 0x00
    b[init_table_gun + 16] = 0x02
    b[init_table_gun + 32] = 0x00
    # gun code
    gun_inc = rom_info.increment_gun_code_4af8
    b[gun_inc + 0] = 0x46  # ram address of current char gun
    b[gun_inc + 1] = 0xc1
    b[gun_inc + 4] = 0x02  # compare value for limit
    b[gun_inc + 8] = rom_info.code_after_increment_gun_7c1e % 256
    b[gun_inc + 9] = rom_info.code_after_increment_gun_7c1e // 256

    scope_inc = rom_info.increment_scope_code_4b07
    scope_code = [33, 73, 193, 126, 183, 192, 52, 33, 106, 194, 203, 254, 201]
    for i in range(13):
        b[scope_inc + i] = scope_code[i]
    b[rom_info.item_pickup_jump_table_4abc + 2 * ID.scope] = scope_inc & 0xff
    b[rom_info.item_pickup_jump_table_4abc + 2 * ID.scope + 1] = scope_inc // 256

    # jump and speed data
    init_table_jump = rom_info.char_init_7b98 + 8  # index 8 is jump
    init_table_speed = init_table_jump - 1
    b[init_table_jump] = 0x01
    b[init_table_speed] = 0x01
    b[init_table_jump + 16] = 0x00
    b[init_table_speed + 16] = 0x00
    b[init_table_jump + 32] = 0x02
    b[init_table_speed + 32] = 0x02

    speed_values = {
        "JJ": [1, 1, 1, 1, 2, 2, 3, 3],
        "Champ": [0, 0, 0, 0, 1, 1, 2, 2],
        "Apple": [2, 2, 2, 2, 3, 3, 3, 3]
    }
    damage_taken_values = {
        "JJ": [3, 3, 3, 3, 2, 2, 2, 1],
        "Champ": [2, 2, 2, 2, 1, 1, 1, 1],
        "Apple": [4, 4, 4, 4, 2, 2, 2, 1]
    }
    jump_base = rom_info.stats_per_level_table_7cc8 + 1
    for char_i, character in enumerate(chars):
        for level_i in range(8):
            jump_addr = jump_base + char_i * 32 + level_i * 4
            b[jump_addr] = char_to_jump[character]["vanilla"][level_i] - 1
            b[jump_addr + 1] = speed_values[character][level_i]
            b[jump_addr + 2] = damage_taken_values[character][level_i]

    b[rom_info.continue_count_init_0af5] = 4
    for addr, v in enumerate(rom_info.continue_dec_code, rom_info.continue_dec_addr_2523):
        b[addr] = v

    b[rom_info.demo_inc] = asm.INCVHL

    for i in range(len(rom_info.game_over_code)):
        a1 = rom_info.game_over_code_retry_24c2 + i
        a2 = rom_info.game_over_code_0_continues_251a + i
        b[a1] = rom_info.game_over_code[i]
        b[a2] = rom_info.game_over_code[i]

    b[rom_info.base_explosion_jump_2112] = 0x89
    b[rom_info.base_explosion_jump_2112 + 1] = 0x06
    b[rom_info.base_explosion_scene_210b] = 0x06

    text = b'=ZILLION= MEN'
    for addr in rom_info.zillion_men_1ae99_1af22:
        b[addr:addr + len(text)] = text

    # splice point for multiworld items
    b[0x73eb] = asm.LDHL
    b[0x73ec] = 0xfe
    b[0x73ed] = 0x75

    for key in verified:
        b[key] = verified[key]
    for key in v_door_data:
        b[key] = v_door_data[key]

    b[rom_info.base_explosion_timer_init_207b] = 0x00
    b[rom_info.base_explosion_timer_init_207b + 1] = 0x03
    b[rom_info.base_explosion_timer_text_6044] = ord("3")
    b[rom_info.base_explosion_timer_text_6044 + 1] = ord("0")
    b[rom_info.base_explosion_timer_text_6044 + 2] = ord("0")

    b[rom_info.init_splice_address_0ac3 + 1] = rom_info.init_splice_target_2e7d & 0xff
    b[rom_info.init_splice_address_0ac3 + 2] = rom_info.init_splice_target_2e7d // 256

    b[rom_info.refill_card_injection_address_1389] = asm.LDHL
    b[rom_info.refill_card_injection_address_1389 + 1] = ram_info.card_count_c129 & 0xff
    b[rom_info.refill_card_injection_address_1389 + 2] = ram_info.card_count_c129 // 256

    b[rom_info.save_hallway_bread_4714] = asm.LDVHLA

    alarm_entrances = [
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x08, 0x98, 0x01, 0x00, 0x00, 0x12,
        0x88, 0xA0, 0x00, 0xFF, 0x00, 0x11,
        0xF0, 0x98, 0xFF, 0x00, 0x00, 0x13,
        0xF0, 0x98, 0xFF, 0x00, 0x01, 0x13,
        0x08, 0x98, 0x01, 0x00, 0x01, 0x12,
        0x90, 0xA0, 0x00, 0xFF, 0x01, 0x11,
        0x50, 0xA0, 0x00, 0xFF, 0x01, 0x11,
        0x30, 0xA0, 0x00, 0xFF, 0x01, 0x11,
        0x70, 0xA0, 0x00, 0xFF, 0x01, 0x11,
        0xD8, 0xA0, 0x00, 0xFF, 0x01, 0x11,
        0x08, 0x98, 0x01, 0x00, 0x02, 0x12,
        0xF0, 0x98, 0xFF, 0x00, 0x02, 0x13,
        0x50, 0xA0, 0x00, 0xFF, 0x02, 0x11,
        0x78, 0xA0, 0x00, 0xFF, 0x02, 0x11,
        0xC0, 0xA0, 0x00, 0xFF, 0x02, 0x11,
    ]
    for i in range(len(alarm_entrances)):
        address = rom_info.alarmed_enemy_entrance_data_7f86 + i
        b[address] = alarm_entrances[i]
