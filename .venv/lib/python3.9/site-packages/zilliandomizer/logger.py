from typing import List


class Logger:
    spoiler_lines: List[str]
    spoil_stdout: bool
    debug_stdout: bool

    def __init__(self) -> None:
        self.spoiler_lines = []
        self.spoil_stdout = False
        self.debug_stdout = False

    def spoil(self, line: str) -> None:
        self.spoiler_lines.append(line)
        if self.spoil_stdout:
            print(line)

    def debug(self, line: str) -> None:
        if self.debug_stdout:
            print(line)

    def warn(self, line: str) -> None:
        print(line)
