from io import StringIO

import pytest
from rich.console import Console

from pos.cli.prompter import Prompter
from pos.container import Container


@pytest.fixture
def container():
    return Container()


@pytest.fixture
def facade(container):
    return container.facade()


@pytest.fixture
def populated(facade):
    facade.add_student("S-001", "Студент Альфа", "БПИ-01")
    facade.add_student("S-002", "Студент Бета")
    facade.add_criterion("HW", "Домашняя работа", 10, 30)
    facade.add_criterion("PROJECT", "Проект", 20, 70)
    return facade


class ScriptedInput:
    def __init__(self, lines):
        self._lines = iter(lines)

    def __call__(self, prompt):
        try:
            return next(self._lines)
        except StopIteration as error:
            raise EOFError from error


@pytest.fixture
def run_app(container, tmp_path):
    def run(*lines, demo=lambda: None):
        output = StringIO()
        console = Console(file=output, width=120, color_system=None)
        container.console.override(console)
        container.prompter.override(Prompter(console, read_line=ScriptedInput(lines)))
        container.app(demo=demo, export_path=str(tmp_path / "results.csv")).run()
        return output.getvalue()

    return run
