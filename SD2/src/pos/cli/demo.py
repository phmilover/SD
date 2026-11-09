from collections.abc import Callable

from pos.application.facade import PosFacade
from pos.cli.view import PosView
from pos.domain.errors import DomainError


class DemoScenario:
    def __init__(self, facade: PosFacade, view: PosView) -> None:
        self._facade = facade
        self._view = view

    def run(self, export_path: str) -> None:
        facade, view = self._facade, self._view
        if facade.students() or facade.criteria():
            raise DomainError("Демо требует отдельную пустую ведомость")
        view.banner(facade.policy_name)
        view.section("1. Студенты и рубрикатор")
        facade.add_student("S-001", "Студент Альфа", "БПИ-01")
        facade.add_student("S-002", "Студент Бета", "БПИ-01")
        facade.add_criterion("HW", "Домашняя работа", 10, 30)
        facade.add_criterion("PROJECT", "Проект", 20, 70)
        view.students(facade.students())
        view.criteria(facade.criteria())

        view.section("2. Выставление оценок и первый итог")
        facade.evaluate("S-001", "HW", 9, "Первая версия")
        facade.evaluate("S-001", "PROJECT", 16)
        facade.evaluate("S-002", "HW", 10)
        view.evaluations(facade.students()[0], facade.evaluations("S-001"))
        view.results(facade.results())

        view.section("3. Защита инвариантов")
        self._rejected("12 из 10", lambda: facade.correct("S-001", "HW", 12))
        self._rejected("Чужой критерий", lambda: facade.evaluate("S-001", "UNKNOWN", 5))
        self._rejected("Дубликат оценки", lambda: facade.evaluate("S-001", "HW", 7))

        view.section("4. Исправление и отмена")
        facade.correct("S-001", "HW", 10, "После исправления")
        view.note(f"После исправления: {facade.result('S-001').final.value:.2f}/10")
        facade.cancel("S-001", "PROJECT")
        view.note(f"После отмены проекта: {facade.result('S-001').final.value:.2f}/10")
        facade.evaluate("S-001", "PROJECT", 16, "Выставлен заново")
        view.results(facade.results())
        view.statistics(facade.statistics())

        view.section("5. Экспорт итогов")
        count = facade.export(export_path)
        view.note(f"Экспортировано строк: {count}. CSV: {export_path}")

    def _rejected(self, title: str, action: Callable[[], object]) -> None:
        try:
            action()
        except DomainError as error:
            self._view.note(f"Ожидаемый отказ ({title}): {error}")
        else:
            raise RuntimeError(f"Нарушение инварианта не отклонено: {title}")
