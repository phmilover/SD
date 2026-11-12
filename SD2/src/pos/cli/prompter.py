from collections.abc import Callable, Sequence
from decimal import Decimal
from typing import TypeVar

from rich.console import Console
from rich.markup import escape

from pos.domain.errors import DomainError
from pos.domain.values import decimal_number

T = TypeVar("T")
ReadLine = Callable[[str], str]


class Prompter:
    def __init__(self, console: Console, read_line: ReadLine | None = None) -> None:
        self._console = console
        self._read_line = read_line or console.input

    def text(self, label: str, *, optional: bool = False) -> str:
        while True:
            value = self._read_line(f"[cyan]›[/] {escape(label)}: ").strip()
            if value or optional:
                return value
            self._warn("Значение не может быть пустым")

    def integer(self, label: str, maximum: int) -> int:
        while True:
            try:
                value = int(self.text(label))
            except ValueError:
                value = -1
            if 0 <= value <= maximum:
                return value
            self._warn(f"Введите целое число от 0 до {maximum}")

    def number(self, label: str, *, maximum: Decimal | None = None) -> Decimal:
        while True:
            try:
                value = decimal_number(self.text(label).replace(",", "."), label)
                if maximum is None and value > 0:
                    return value
                if maximum is not None and 0 <= value <= maximum:
                    return value
            except DomainError as error:
                self._warn(str(error))
                continue
            message = "Введите положительное конечное число"
            if maximum is not None:
                message = f"Введите конечное число от 0 до {maximum}"
            self._warn(message)

    def choice(self, title: str, options: Sequence[tuple[str, T]]) -> T | None:
        if not options:
            self._warn(f"{title}: список пуст")
            return None
        self._console.print(escape(title), style="bold")
        for index, (label, _) in enumerate(options, 1):
            self._console.print(f"  {index}. {escape(label)}")
        self._console.print("  0. Назад")
        index = self.integer("Номер", len(options))
        return options[index - 1][1] if index else None

    def _warn(self, message: str) -> None:
        self._console.print(escape(message), style="yellow")
