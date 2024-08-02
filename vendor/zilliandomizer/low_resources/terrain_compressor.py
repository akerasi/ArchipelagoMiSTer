from typing import ClassVar, List, Literal


class TerrainCompressor:
    BANK_OFFSET: ClassVar[int] = 0x8000

    @staticmethod
    def decompress(_bytes: List[int]) -> List[int]:
        tr: List[int] = []
        cursor = 0
        while cursor < len(_bytes):
            command = _bytes[cursor]
            cursor += 1
            if command & 0x80:
                number = command & 0x7f
                for _ in range(number):
                    tr.append(_bytes[cursor])
                    cursor += 1
            else:  # no MSB set
                number = command
                for _ in range(number):
                    tr.append(_bytes[cursor])
                cursor += 1

        return tr

    @staticmethod
    def compress(_bytes: List[int]) -> List[int]:
        assert len(_bytes) == 96
        tr: List[int] = []
        current_state: Literal["length", "copy"] = "length"
        cursor = 0
        copy_address = -1
        while cursor < len(_bytes):
            count = 1
            current_byte = _bytes[cursor]
            cursor += 1
            while cursor < len(_bytes) and _bytes[cursor] == current_byte:
                count += 1
                cursor += 1
            if current_state == "copy":
                if count < 3:
                    # stay copy
                    tr.extend([current_byte] * count)
                    tr[copy_address] += count
                else:  # count > 2
                    # change state
                    current_state = "length"
                    tr.append(count)
                    tr.append(current_byte)
            else:  # length
                if count == 1:
                    current_state = "copy"
                    copy_address = len(tr)
                    tr.append(0x81)
                    tr.append(current_byte)
                else:  # count > 1
                    # stay length
                    tr.append(count)
                    tr.append(current_byte)
        tr.append(0x00)
        return tr
