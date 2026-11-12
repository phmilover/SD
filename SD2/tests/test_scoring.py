from decimal import Decimal

import pytest

from pos.domain.errors import DomainError
from pos.domain.model import Criterion, Gradebook, Student
from pos.domain.scoring import AssessedOnly, FinalScoreService, WeightedAverage


def test_weighted_result_normalizes_different_scales_and_weights(populated):
    populated.evaluate("S-001", "HW", 9)
    populated.evaluate("S-001", "PROJECT", 16)
    result = populated.result("S-001").final
    assert result.value == Decimal("8.30")
    assert result.complete
    assert (result.assessed, result.total) == (2, 2)


def test_missing_score_is_zero_and_not_excluded_from_denominator(populated):
    populated.evaluate("S-001", "HW", 10)
    result = populated.result("S-001").final
    assert result.value == Decimal("3.00")
    assert not result.complete
    assert (result.assessed, result.total) == (1, 2)
    assert populated.result("S-002").final.value == Decimal("0.00")


def test_explicit_zero_counts_as_evaluated(populated):
    populated.evaluate("S-001", "HW", 0)
    populated.evaluate("S-001", "PROJECT", 0)
    result = populated.result("S-001").final
    assert result.complete
    assert result.value == 0


def test_correction_cancellation_and_new_criterion_recalculate_result(populated):
    populated.evaluate("S-001", "HW", 9)
    populated.evaluate("S-001", "PROJECT", 16)
    assert populated.result("S-001").final.value == Decimal("8.30")
    populated.correct("S-001", "HW", 10)
    assert populated.result("S-001").final.value == Decimal("8.60")
    populated.cancel("S-001", "PROJECT")
    assert populated.result("S-001").final.value == Decimal("3.00")
    populated.add_criterion("EXAM", "Экзамен", 10, 100)
    result = populated.result("S-001").final
    assert result.value == Decimal("1.50")
    assert result.total == 3


def test_weights_need_not_sum_to_one_and_common_scaling_does_not_change_result():
    results = []
    for scale in (Decimal("0.01"), Decimal(1), Decimal(100)):
        book = Gradebook("KPO", "КПО")
        book.add_student(Student("S", "Студент"))
        for code, maximum, weight, score in (("HW", 10, 30, 9), ("PROJECT", 20, 70, 16)):
            book.add_criterion(Criterion(code, code, maximum, Decimal(weight) * scale))
            book.record_evaluation("S", code, score)
        results.append(FinalScoreService(WeightedAverage()).calculate(book, "S").value)
    assert results == [Decimal("8.30")] * 3


def test_rounding_uses_half_up_once_at_the_end(facade):
    facade.add_student("S", "Студент")
    facade.add_criterion("ONE", "Один критерий", 10000, 1)
    facade.evaluate("S", "ONE", 1235)
    assert facade.result("S").final.value == Decimal("1.24")


@pytest.mark.parametrize("weights", [(1, 6), (1, 7), (3, 7)])
def test_repeating_weight_fractions_do_not_shift_a_rounding_tie(facade, weights):
    facade.add_student("S", "Студент")
    for code, weight in zip(("A", "B"), weights, strict=True):
        facade.add_criterion(code, code, 2000, weight)
        facade.evaluate("S", code, 247)
    assert facade.result("S").final.value == Decimal("1.24")


def test_empty_rubric_has_no_meaningful_final_score(facade):
    facade.add_student("S", "Студент")
    with pytest.raises(DomainError, match="рубрикатор пуст"):
        facade.result("S")


def test_strategy_can_be_replaced_via_di_without_changing_use_cases(container):
    container.config.policy.from_value("assessed")
    facade = container.facade()
    facade.add_student("S", "Студент")
    facade.add_criterion("HW", "ДЗ", 10, 30)
    facade.add_criterion("PROJECT", "Проект", 20, 70)
    assert facade.result("S").final.value == 0
    facade.evaluate("S", "HW", 9)
    result = facade.result("S").final
    assert result.value == Decimal("9.00")
    assert not result.complete
    assert result.policy.startswith("Предварительный")
    assert isinstance(container.scoring_strategy(), AssessedOnly)


def test_strategies_agree_for_complete_gradebook(populated, container):
    populated.evaluate("S-001", "HW", "7.5")
    populated.evaluate("S-001", "PROJECT", 13)
    book = container.repository().load()
    regular = FinalScoreService(WeightedAverage()).calculate(book, "S-001")
    preview = FinalScoreService(AssessedOnly()).calculate(book, "S-001")
    assert regular.value == preview.value == Decimal("6.80")
