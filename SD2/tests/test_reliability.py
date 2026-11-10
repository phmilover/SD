from decimal import Decimal
from fractions import Fraction

import pytest

from pos.adapters.memory import InMemoryGradebookRepository
from pos.domain.errors import DomainError
from pos.domain.model import Criterion, Gradebook, Student
from pos.domain.ports import GradebookRepository
from pos.domain.scoring import FinalScore, FinalScoreService, ScoringStrategy
from pos.domain.values import Score, decimal_number, round_hundredths
from tests.test_csv_export import read_csv


def test_repository_owns_initial_snapshot_and_keeps_course_identity():
    initial = Gradebook("KPO", "КПО")
    repository = InMemoryGradebookRepository(initial)
    initial.add_student(Student("S", "Студент"))
    assert repository.load().students == ()
    with pytest.raises(DomainError, match="другим курсом"):
        repository.save(Gradebook("OTHER", "Другой курс"))
    assert repository.load().code == "KPO"


def test_failed_save_can_be_retried_without_leaking_uncommitted_evaluation(container):
    class UnreliableRepository(InMemoryGradebookRepository):
        fail = True

        def save(self, gradebook):
            if self.fail:
                raise OSError("Ошибка сохранения")
            super().save(gradebook)

    initial = Gradebook("KPO", "КПО")
    initial.add_student(Student("S", "Студент"))
    initial.add_criterion(Criterion("HW", "ДЗ", 10, 1))
    repository = UnreliableRepository(initial)
    container.repository.override(repository)
    facade = container.facade()
    with pytest.raises(OSError, match="сохранения"):
        facade.evaluate("S", "HW", 7)
    assert facade.evaluations("S") == ()
    repository.fail = False
    facade.evaluate("S", "HW", 8)
    assert facade.result("S").final.value == Decimal("8.00")


@pytest.mark.parametrize("operation", ["results", "statistics", "export"])
def test_read_operation_uses_a_single_consistent_snapshot(
    operation, populated, container, tmp_path
):
    populated.evaluate("S-001", "HW", 9)
    populated.evaluate("S-001", "PROJECT", 16)
    snapshot = container.repository().load()

    class ChangingRepository(GradebookRepository):
        reads = 0

        def load(self):
            self.reads += 1
            return snapshot if self.reads == 1 else Gradebook("KPO", "КПО")

        def save(self, gradebook):
            raise AssertionError("Чтение не должно сохранять ведомость")

    repository = ChangingRepository()
    container.repository.override(repository)
    container.facade.reset()
    facade = container.facade()
    if operation == "export":
        path = tmp_path / "results.csv"
        assert facade.export(str(path)) == 2
        assert read_csv(path)[0]["Итог из 10"] == "8.30"
    elif operation == "statistics":
        assert facade.statistics().average == Decimal("4.15")
    else:
        assert facade.results()[0].final.value == Decimal("8.30")
    assert repository.reads == 1


def test_evaluations_are_isolated_between_students(populated):
    populated.evaluate("S-001", "HW", 8)
    populated.evaluate("S-002", "HW", 5)
    populated.correct("S-001", "HW", 9)
    populated.cancel("S-001", "HW")
    assert populated.evaluations("S-001") == ()
    assert populated.evaluations("S-002")[0].score.value == 5


@pytest.mark.parametrize("value", [0.1, True, None, [], {}])
def test_number_api_rejects_implicit_or_lossy_conversions(value):
    with pytest.raises(DomainError):
        decimal_number(value, "Балл")


@pytest.mark.parametrize("value", ["1e999999999", "1e-999999999", "1e10", "1e-10"])
def test_extreme_numbers_are_rejected_before_fraction_arithmetic(value):
    with pytest.raises(DomainError, match="от 1e-9 до 1e9"):
        Score(value, value)


@pytest.mark.parametrize("value", ["1e9", "1e-9", "999999999"])
def test_boundary_numbers_are_supported(value):
    assert Score(value, value).fraction == 1


@pytest.mark.parametrize("value,expected", [("16.0", "16"), ("1.50", "1.5"), ("0e999999999", "0")])
def test_equivalent_notations_are_normalized_without_rounding(value, expected):
    assert str(decimal_number(value, "Балл")) == expected


@pytest.mark.parametrize("field", ["name", "group"])
def test_wrong_text_types_produce_domain_error(field):
    values = {"code": "S", "name": "Студент", "group": "БПИ"}
    values[field] = None
    with pytest.raises(DomainError, match="строка"):
        Student(**values)


@pytest.mark.parametrize("value,expected", [("1.235", "1.24"), ("-1.235", "-1.24")])
def test_half_up_rounding_is_exact(value, expected):
    assert round_hundredths(Fraction(value)) == Decimal(expected)


@pytest.mark.parametrize("value", [Fraction(-1, 1000), Fraction(10001, 1000)])
def test_invalid_strategy_result_is_rejected_before_rounding(value, container, populated):
    class InvalidStrategy(ScoringStrategy):
        name = "Некорректное правило"

        def calculate(self, criteria, evaluations):
            return value

    service = FinalScoreService(InvalidStrategy())
    with pytest.raises(DomainError, match="вне диапазона"):
        service.calculate(container.repository().load(), "S-001")


@pytest.mark.parametrize(
    "value,assessed,total",
    [(11, 1, 1), (-1, 1, 1), (8, -1, 1), (8, 2, 1), (8, 0, 0)],
)
def test_final_score_cannot_represent_an_impossible_value_or_completeness(value, assessed, total):
    with pytest.raises(DomainError):
        FinalScore(value, assessed, total, "По весам")
