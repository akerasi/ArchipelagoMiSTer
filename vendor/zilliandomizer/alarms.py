from random import random, choice
from typing import Dict, FrozenSet, List, Literal, Set
from zilliandomizer.alarm_data import ALARM_ROOMS, Alarm, alarm_data, to_horizontal, to_vertical, to_none
from zilliandomizer.terrain_modifier import TerrainModifier
from zilliandomizer.logger import Logger
from zilliandomizer.low_resources.terrain_compressor import TerrainCompressor


class Alarms:
    """
    Anything else modifying terrain needs to be done before initializing this object,
    because this could use all of the space for terrain.
    """
    tc: TerrainModifier
    _space_pacer_init: float  # I wanted to use `typing.Final` here, but mypy doesn't allow that
    """ how many extra bytes we start with before choosing alarms """
    _space_pacer: float
    """ what the space available should be if using the space gradually """
    _space_per_room: float  # I wanted to use `typing.Final` here, but mypy doesn't allow that
    """
    the ideal number of extra bytes to use for each room
    """
    _logger: Logger

    def __init__(self, tc: TerrainModifier, logger: Logger) -> None:
        self.tc = tc
        self._space_pacer_init = tc.get_space()
        self._space_pacer = self._space_pacer_init
        # This is assuming that we are the last step modifying terrain,
        # because this could use all of the space for terrain.
        # So, anything else modifying terrain needs to be done before initializing this object.
        self._space_per_room = self._space_pacer / len(ALARM_ROOMS)
        self._logger = logger
        # testing
        # logger.spoil_stdout = True
        # logger.debug_stdout = True

    def choose_all(self, skip_map_index: FrozenSet[int]) -> None:
        # TODO: I haven't tested the tc save state and success loop yet
        self.tc.save_state()
        success = False  # chose all alarm lines without going over the byte limit
        while not success:
            self._logger.spoil("choosing alarm lines...")
            self._space_pacer = self._space_pacer_init
            for map_index in ALARM_ROOMS:
                if map_index in alarm_data and map_index not in skip_map_index:
                    self._choose_for_room(map_index)
                self._space_pacer -= self._space_per_room
            if self.tc.get_space() >= 0:
                success = True
            else:
                self.tc.load_state()

    def _choose_for_room(self, map_index: int) -> None:
        this_room = alarm_data[map_index]
        chosen: Set[str] = set()
        eliminated: Set[str] = set()  # chosen already, or conflicting with chosen
        lessened: Set[str] = set()

        vanilla_alarm_count = sum(a.vanilla for a in this_room)
        self._logger.debug(f"vanilla alarms in this room: {vanilla_alarm_count}")

        pace_diff = self.tc.get_space() - self._space_pacer
        self._logger.debug(f"choosing room {map_index} with pace_diff {pace_diff:.4f}")
        pace_diff = pace_diff + 2 * (vanilla_alarm_count - 1) - 5
        self._logger.debug(f"adjusted pace_diff from vanilla: {pace_diff:.4f}")
        prob = 1.0
        prob_mult: float = 0.5 + ((map_index // 8) ** 0.5 * 0.1)
        """
        some explanation of the magic numbers here and some info from experiments:

        Assuming an infinite number of available alarm lines,
        the following table is a mapping of the expected number of alarm lines
        to the prob_mult that will produce this expected number.

        I couldn't find a simple equation for this function.
        I'm curious whether there is one.
        It looks like there's not:
        https://math.stackexchange.com/questions/4494669/roll-until-lose-game-with-changing-probability/4494686#4494686
        ```
        e = {
            1.0: 0.0,
            1.01: 0.01,
            1.1: 0.099,
            1.25: 0.238,
            1.5: 0.42,
            2.0: 0.645,
            3.0: 0.833,
            4.0: 0.904,
            5.0: 0.938,
            6.0: 0.957,
            7.0: 0.9685,
        }
        ```

        We want always at least 1 alarm line in the rooms that can have alarm lines.
        The number of alarm lines in vanilla is (very) roughly proportional to the map row.
        """
        if pace_diff < 0:  # so far, used more bytes than is sustainable
            # reduce the probability of more alarm lines
            prob_mult -= 0.05 * (-pace_diff)
            self._logger.debug(f"reduced prob_mult to {prob_mult}")
            # if this goes negative, then the next multiplication with prob will be negative,
            # so the loop will stop (so it won't be multiplied again to go back to positive)
        else:  # we have bytes to spare
            # so raise the probability
            increases = pace_diff / 10  # tunable magic number, raise if failing to place alarms too much
            # average with 1 with this much weight on the 1
            self._logger.debug(f"increasing prob_mult from {prob_mult} to {(prob_mult + increases) / (increases + 1)}")
            prob_mult = (prob_mult + increases) / (increases + 1)
            assert prob_mult < 1, f"sanity check on increasing prob_mult {prob_mult}, pace_diff {pace_diff}"
        while (len(eliminated) < len(this_room)) and random() < (
            # usually at least as many alarms as vanilla, and unlikely to have many more
            (prob * 0.3) if len(chosen) >= vanilla_alarm_count else prob
        ):
            choices: List[Alarm] = [a for a in this_room if a.id not in eliminated]
            n = len(choices)  # not changing during iteration
            for i in range(n):
                if choices[i].id not in lessened:
                    choices.append(choices[i])  # add an extra chance to choose this alarm
                    if (pace_diff > 0) or (not choices[i].vertical):
                        # if bytes to spare or horizontal, add another chance to choose this alarm
                        choices.append(choices[i])
                        # Because of run-length encoding that moves horizontally,
                        # most horizontal alarm lines don't cost any extra bytes.
                        # The vertical ones are the expensive ones,
                        # because they break the horizontal run.

            this_choice = choice(choices)
            chosen.add(this_choice.id)
            eliminated.update(this_choice.disables)
            eliminated.add(this_choice.id)
            lessened.update(this_choice.lessens)

            prob *= prob_mult
            # TODO: which rooms should have more/fewer alarm lines
            # change probability according to that

            # TODO: skill level could disable lessened and
            # change probability of more alarms

        # testing d601
        # if 0x20 < map_index < 0x30:
        #     chosen = {a.id for a in this_room if a.vertical}
        #     chosen = set()

        self._logger.spoil(f"room: {map_index}  chosen: {chosen}")
        _bytes = TerrainCompressor.decompress(self.tc.get_room(map_index))
        assert len(_bytes) == 96, f"room {map_index} doesn't have the right number of bytes: {len(_bytes)}"

        # gather all the blocks involved
        blocks: Dict[int, Literal["v", "h", "n"]] = {}  # key block_index
        for a in this_room:
            for block_index, erase in a.block_iter():
                # verify
                # since this isn't the Patcher class, I don't have access to its self.verify
                # don't know whether I need these assertions...
                # I like them to help me find errors, but it might cause trouble
                # if I have have a reason to turn verify off in Patcher.
                if a.vanilla and erase:
                    if a.vertical:
                        assert _bytes[block_index] == to_vertical[_bytes[block_index]], \
                            f"vanilla vertical map {map_index} block {block_index}"
                    else:  # horizontal
                        assert _bytes[block_index] == to_horizontal[_bytes[block_index]], \
                            f"vanilla horizontal map {map_index} block {block_index}"
                # else not vanilla - can't verify because it might cross a vanilla

                if a.id in chosen and not erase:
                    blocks[block_index] = "v" if a.vertical else "h"
                else:
                    if block_index not in blocks:
                        blocks[block_index] = "n"

        Alarms.add_alarms_to_room_terrain_bytes(_bytes, blocks)

        self.tc.set_room(map_index, TerrainCompressor.compress(_bytes))

    @staticmethod
    def add_alarms_to_room_terrain_bytes(
        bytes_: List[int],
        blocks: Dict[int, Literal["v", "h", "n"]]
    ) -> None:
        """
        `bytes_` is length 96 of what `TerrainCompressor` deals with.
        `bytes_` will be modified in place.

        `blocks` is map of changes that need to be made for alarms,
        index: Literal["v", "h", "n"]
        """
        for block_index in blocks:
            block = blocks[block_index]
            to = to_vertical if block == "v" \
                else (to_horizontal if block == "h" else to_none)
            bytes_[block_index] = to[bytes_[block_index]]
