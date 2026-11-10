from decimal import Decimal

import pytest

from pos.adapters.memory import InMemoryGradebookRepository
from pos.application.ports import ResultsExporter
from pos.domain.errors import DomainError, DuplicateError
from pos.domain.model import Gradebook, Student


def test_repository_load_and_save_are_independent_snapshots():
    repository = InMemoryGradebookRepository(Gradebook("KPO", "КПО"))
    book = repository.load()
    book.add_student(Student("S", "Студент"))
    assert repository.load().students == ()
    repository.save(book)
    book.add_student(Student("T", "Другой"))
    assert [s.code for s in repository.load().students] == ["S"]


def test_failed_use_case_does_not_change_persisted_state(populated):
    populated.evaluate("S-001", "HW", 8)
    with pytest.raises(DomainError):
        populated.correct("S-001", "HW", 12)
    with pytest.raises(DuplicateError):
        populated.add_student("S-001", "Дубликат")
    assert populated.evaluations("S-001")[0].score.value == 8
    assert len(populated.students()) == 2


def test_course_statistics_include_students_with_missing_scores(populated):
    populated.evaluate("S-001", "HW", 10)
    populated.evaluate("S-001", "PROJECT", 20)
    populated.evaluate("S-002", "HW", 5)
    stats = populated.statistics()
    assert (stats.students, stats.criteria, stats.evaluations, stats.complete_students) == (
        2,
        2,
        3,
        1,
    )
    assert (stats.average, stats.minimum, stats.maximum) == (
        Decimal("5.75"),
        Decimal("1.50"),
        Decimal("10.00"),
    )


def test_statistics_of_empty_course_has_no_artificial_average(facade):
    stats = facade.statistics()
    assert stats.students == stats.criteria == stats.evaluations == stats.complete_students == 0
    assert stats.average is stats.minimum is stats.maximum is None


def test_facade_uses_export_port_with_current_results(container, populated):
    class RecordingExporter(ResultsExporter):
        def export(self, results, destination):
            self.results, self.destination = results, destination

    exporter = RecordingExporter()
    populated.evaluate("S-001", "HW", 10)
    populated.correct("S-001", "HW", 5)
    with container.exporter.override(exporter):
        container.facade.reset()
        assert container.facade().export("target") == 2
    assert exporter.destination == "target"
    assert exporter.results[0].final.value == Decimal("1.50")


def test_repository_can_be_replaced_before_use_case_graph_is_built(container):
    replacement = InMemoryGradebookRepository(Gradebook("KPO", "КПО"))
    with container.repository.override(replacement):
        container.facade().add_student("S", "Студент")
        assert replacement.load().student("S").name == "Студент"
    assert container.repository().load().students == ()


def test_containers_do_not_share_state(container):
    from pos.container import Container

    container.facade().add_student("S", "Студент")
    assert Container().facade().students() == ()


def test_export_empty_rubric_does_not_create_file(facade, tmp_path):
    path = tmp_path / "results.csv"
    with pytest.raises(DomainError, match="рубрикатор пуст"):
        facade.export(str(path))
    assert not path.exists()
