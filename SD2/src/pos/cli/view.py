from collections.abc import Sequence

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from pos.application.reports import CourseStatistics, StudentResult
from pos.domain.model import Criterion, Evaluation, Student


class PosView:
    def __init__(self, console: Console) -> None:
        self._console = console

    def banner(self, policy: str) -> None:
        self._console.print(
            Panel.fit("[bold cyan]ПОС[/] — преподавательская оценка студентов", border_style="cyan")
        )
        self.note(f"Правило итога: {policy}. Шкала: 0–10.")
        self.note("Данные хранятся в памяти до выхода. CSV сохраняется отдельно.")

    def menu(self, titles: Sequence[str]) -> None:
        table = Table(show_header=False, box=None)
        for index, title in enumerate(titles, 1):
            table.add_row(str(index), title)
        table.add_row("0", "Выход")
        self._console.print(Panel(table, title="Меню", expand=False))

    def section(self, title: str) -> None:
        self._console.rule(escape(title), align="left", style="cyan")

    def note(self, message: str) -> None:
        self._console.print(escape(message))

    def error(self, message: str) -> None:
        self._console.print(f"[bold red]Ошибка:[/] {escape(message)}")

    def goodbye(self) -> None:
        self.note("До встречи! Обратная связь — спорт для двоих.")

    def students(self, students: Sequence[Student]) -> None:
        self._table(
            "Студенты", ("Код", "Имя", "Группа"), [(s.code, s.name, s.group) for s in students]
        )

    def criteria(self, criteria: Sequence[Criterion]) -> None:
        self._table(
            "Рубрикатор",
            ("Код", "Критерий", "Максимум", "Вес"),
            [(c.code, c.name, str(c.max_score), str(c.weight)) for c in criteria],
        )

    def evaluations(self, student: Student, evaluations: Sequence[Evaluation]) -> None:
        self._table(
            f"Оценки: {student.name} ({student.code})",
            ("Критерий", "Балл", "Максимум", "Комментарий"),
            [
                (e.criterion.name, str(e.score.value), str(e.score.maximum), e.comment)
                for e in evaluations
            ],
        )

    def results(self, results: Sequence[StudentResult]) -> None:
        self._table(
            "Итоги по студентам (из 10)",
            ("Код", "Студент", "Итог", "Оценено", "Полнота"),
            [
                (
                    r.student.code,
                    r.student.name,
                    f"{r.final.value:.2f}",
                    f"{r.final.assessed}/{r.final.total}",
                    "Все оценки" if r.final.complete else "Есть пропуски",
                )
                for r in results
            ],
        )

    def statistics(self, stats: CourseStatistics) -> None:
        self.note(
            f"Студентов: {stats.students}; критериев: {stats.criteria}; "
            f"оценок: {stats.evaluations}; полностью оценено: {stats.complete_students}."
        )
        if stats.average is None:
            self.note("Средний, минимальный и максимальный итог: нет данных.")
        else:
            self.note(
                f"Средний итог: {stats.average:.2f}; минимум: {stats.minimum:.2f}; "
                f"максимум: {stats.maximum:.2f}."
            )

    def _table(self, title: str, columns: tuple[str, ...], rows: Sequence[tuple[str, ...]]) -> None:
        self.section(title)
        if not rows:
            self.note("Список пуст.")
            return
        table = Table(*columns, box=box.ROUNDED, header_style="bold cyan")
        for row in rows:
            table.add_row(*(escape(cell) for cell in row))
        self._console.print(table)
