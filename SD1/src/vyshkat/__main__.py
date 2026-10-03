"""Точка входа: `python -m vyshkat` — меню, `python -m vyshkat --demo` — демо без ввода."""

import argparse
from collections.abc import Sequence

from vyshkat.cli.demo import load_pilot_park
from vyshkat.container import Container


def run_demo() -> None:
    """Демо всегда идёт на отдельном контейнере — то есть на пустом парке."""
    Container().demo().run()


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="vyshkat", description="ВышКат — учёт парка")
    parser.add_argument("--demo", action="store_true", help="показать все сценарии без ввода")
    args = parser.parse_args(argv)

    if args.demo:
        run_demo()
        return

    container = Container()
    load_pilot_park(container.intake())
    container.app(demo=run_demo).run()


if __name__ == "__main__":
    main()
