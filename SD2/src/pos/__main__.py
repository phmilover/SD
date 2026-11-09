import argparse
from collections.abc import Sequence

from pos.container import Container
from pos.domain.errors import DomainError


def make_container(policy: str) -> Container:
    container = Container()
    container.config.policy.from_value(policy)
    return container


def run_demo(policy: str, export_path: str) -> None:
    make_container(policy).demo().run(export_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hse-pos", description="ПОС — оценивание студентов")
    parser.add_argument("--demo", action="store_true", help="сквозной сценарий без ввода")
    parser.add_argument(
        "--policy",
        choices=("weighted", "assessed"),
        default="weighted",
        help="weighted: пропуски = 0; assessed: предварительный итог по выставленным оценкам",
    )
    parser.add_argument("--export", help="путь CSV (существующий файл будет перезаписан)")
    args = parser.parse_args(argv)
    container = make_container(args.policy)
    try:
        if args.demo:
            container.demo().run(args.export or "exports/demo-results.csv")
        else:
            container.app(
                demo=lambda: run_demo(args.policy, args.export or "exports/demo-results.csv"),
                export_path=args.export or "exports/results.csv",
            ).run()
    except (DomainError, OSError) as error:
        container.view().error(str(error))
        return 1
    except KeyboardInterrupt:
        container.view().goodbye()
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
