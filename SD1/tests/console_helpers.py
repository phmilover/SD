"""Консоль для тестов: ввод по сценарию, вывод в строку."""

import io
from collections.abc import Iterable

from rich.console import Console


class ScriptedInput:
    """Подменяет console.input: отдаёт строки по очереди, в конце — EOF (как Ctrl+D)."""

    def __init__(self, lines: Iterable[str]) -> None:
        self._lines = iter(lines)

    def __call__(self, prompt: str = "") -> str:
        try:
            return next(self._lines)
        except StopIteration:
            raise EOFError from None


def recording_console() -> tuple[Console, io.StringIO]:
    buffer = io.StringIO()
    console = Console(file=buffer, width=120, color_system=None, emoji=False)
    return console, buffer
