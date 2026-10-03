"""Ввод с консоли: каждый метод переспрашивает, пока значение некорректно."""

import math
from collections.abc import Callable, Sequence
from typing import TypeVar

from rich.console import Console
from rich.markup import escape

ReadLine = Callable[[str], str]
T = TypeVar("T")


class Prompter:
    def __init__(self, console: Console, read_line: ReadLine | None = None) -> None:
        self._console = console
        # В тестах сюда подставляется ввод по сценарию.
        self._read_line = read_line or console.input

    def text(self, label: str) -> str:
        while True:
            value = self._ask(label).strip()
            if value:
                return value
            self._warn("Значение не может быть пустым")

    def integer(self, label: str, minimum: int, maximum: int) -> int:
        while True:
            try:
                value = int(self._ask(label).strip())
            except ValueError:
                value = None
            if value is not None and minimum <= value <= maximum:
                return value
            self._warn(f"Введите целое число от {minimum} до {maximum}")

    def number(self, label: str) -> float:
        """Положительное число; принимает и точку, и запятую."""
        while True:
            try:
                value = float(self._ask(label).strip().replace(",", "."))
            except ValueError:
                value = None
            if value is not None and math.isfinite(value) and value > 0:
                return value
            self._warn("Введите положительное число, например 0.45")

    def items(self, label: str) -> tuple[str, ...]:
        """Список через запятую; пустой ответ — пустой список."""
        return tuple(part.strip() for part in self._ask(label).split(",") if part.strip())

    def choice(self, title: str, options: Sequence[tuple[str, T]]) -> T | None:
        """Выбор из списка; 0 — «Назад» (возвращает None)."""
        if not options:
            raise ValueError("Нечего выбирать: список вариантов пуст")
        self._console.print(f"[bold]{escape(title)}:[/]")
        for number, (caption, _) in enumerate(options, start=1):
            self._console.print(f"  [cyan]{number}.[/] {escape(caption)}")
        self._console.print("  [cyan]0.[/] Назад")
        selected = self.integer("Номер", 0, len(options))
        return options[selected - 1][1] if selected else None

    def _ask(self, label: str) -> str:
        return self._read_line(f"[bold cyan]›[/] {escape(label)}: ")

    def _warn(self, message: str) -> None:
        self._console.print(f"  [yellow]{escape(message)}[/]")
