from collections.abc import Callable

from pos.application.facade import PosFacade
from pos.cli.prompter import Prompter
from pos.cli.view import PosView
from pos.domain.errors import DomainError, DuplicateError
from pos.domain.model import Criterion, Evaluation, Student
from pos.domain.values import normalize_code


class ConsoleApp:
    def __init__(
        self,
        facade: PosFacade,
        prompter: Prompter,
        view: PosView,
        demo: Callable[[], None],
        export_path: str = "exports/results.csv",
    ) -> None:
        self._facade = facade
        self._prompter = prompter
        self._view = view
        self._export_path = export_path
        self._actions: list[tuple[str, Callable[[], None]]] = [
            ("Добавить студента", self._add_student),
            ("Список студентов", lambda: view.students(facade.students())),
            ("Добавить критерий", self._add_criterion),
            ("Рубрикатор", lambda: view.criteria(facade.criteria())),
            ("Выставить оценку", self._evaluate),
            ("Оценки студента", self._evaluations),
            ("Исправить оценку", self._correct),
            ("Отменить оценку", self._cancel),
            ("Итоги по студентам", lambda: view.results(facade.results())),
            ("Аналитика курса", lambda: view.statistics(facade.statistics())),
            ("Экспорт итогов в CSV", self._export),
            ("Демо (в отдельной пустой ведомости)", demo),
        ]

    def run(self) -> None:
        self._view.banner(self._facade.policy_name)
        try:
            while True:
                self._view.menu([title for title, _ in self._actions])
                choice = self._prompter.integer("Пункт меню", len(self._actions))
                if not choice:
                    break
                try:
                    self._actions[choice - 1][1]()
                except (DomainError, OSError) as error:
                    self._view.error(str(error))
        except (EOFError, KeyboardInterrupt):
            pass
        self._view.goodbye()

    def _add_student(self) -> None:
        code = self._new_code({s.code for s in self._facade.students()})
        student = self._facade.add_student(
            code, self._prompter.text("Имя студента"), self._prompter.text("Группа", optional=True)
        )
        self._view.note(f"Студент {student.code} добавлен.")

    def _add_criterion(self) -> None:
        code = self._new_code({c.code for c in self._facade.criteria()})
        criterion = self._facade.add_criterion(
            code,
            self._prompter.text("Название критерия"),
            self._prompter.number("Максимальный балл (> 0)"),
            self._prompter.number("Вес (> 0, например 30 или 0,3)"),
        )
        self._view.note(f"Критерий {criterion.code} добавлен.")

    def _evaluate(self) -> None:
        student = self._choose_student()
        if student is None:
            return
        criterion = self._choose_criterion()
        if criterion is None:
            return
        evaluation = self._facade.evaluate(
            student.code,
            criterion.code,
            self._prompter.number("Балл", maximum=criterion.max_score),
            self._prompter.text("Комментарий (Enter — без комментария)", optional=True),
        )
        self._view.note(f"Оценка выставлена: {evaluation.score.value}/{criterion.max_score}.")

    def _evaluations(self) -> None:
        student = self._choose_student()
        if student is not None:
            self._view.evaluations(student, self._facade.evaluations(student.code))

    def _correct(self) -> None:
        evaluation = self._choose_evaluation()
        if evaluation is not None:
            self._facade.correct(
                evaluation.student_code,
                evaluation.criterion.code,
                self._prompter.number("Новый балл", maximum=evaluation.criterion.max_score),
                self._prompter.text("Новый комментарий (Enter — оставить прежний)", optional=True)
                or evaluation.comment,
            )
            self._view.note("Оценка исправлена; итог будет пересчитан.")

    def _cancel(self) -> None:
        evaluation = self._choose_evaluation()
        if evaluation is not None:
            self._facade.cancel(evaluation.student_code, evaluation.criterion.code)
            self._view.note("Оценка отменена; итог будет пересчитан.")

    def _export(self) -> None:
        path = (
            self._prompter.text(
                f"Путь CSV (Enter — {self._export_path}; существующий файл будет перезаписан)",
                optional=True,
            )
            or self._export_path
        )
        count = self._facade.export(path)
        self._view.note(f"Экспортировано строк: {count}. CSV: {path}")

    def _choose_student(self) -> Student | None:
        return self._prompter.choice(
            "Студент", [(f"{s.code} — {s.name}", s) for s in self._facade.students()]
        )

    def _choose_criterion(self) -> Criterion | None:
        return self._prompter.choice(
            "Критерий",
            [(f"{c.code} — {c.name} (максимум {c.max_score})", c) for c in self._facade.criteria()],
        )

    def _choose_evaluation(self) -> Evaluation | None:
        student = self._choose_student()
        if student is None:
            return None
        return self._prompter.choice(
            "Выставленная оценка",
            [
                (f"{e.criterion.code}: {e.score.value}/{e.score.maximum}", e)
                for e in self._facade.evaluations(student.code)
            ],
        )

    def _new_code(self, occupied: set[str]) -> str:
        while True:
            try:
                code = normalize_code(self._prompter.text("Код (например S-001)"))
                if code in occupied:
                    raise DuplicateError(f"Код {code} уже используется")
                return code
            except DomainError as error:
                self._view.error(str(error))
