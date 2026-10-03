import pytest

from tests.console_helpers import ScriptedInput, recording_console
from vyshkat.cli.prompter import Prompter
from vyshkat.container import Container


@pytest.fixture
def container():
    """Свежий контейнер на каждый тест: у каждого теста свой пустой парк."""
    container = Container()
    yield container
    container.reset_override()


@pytest.fixture
def run_app(container):
    """Запускает меню с заданным вводом и возвращает весь вывод."""

    def run(*lines: str, demo=None) -> str:
        console, output = recording_console()
        container.console.override(console)
        container.prompter.override(Prompter(console, read_line=ScriptedInput(lines)))
        container.app(demo=demo or (lambda: None)).run()
        return output.getvalue()

    return run
