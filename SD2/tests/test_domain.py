from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from pos.domain.errors import DomainError, DuplicateError, NotFoundError
from pos.domain.model import Criterion, Evaluation, Gradebook, Student
from pos.domain.values import Score, decimal_number, normalize_code


@pytest.fixture
def book():
    book = Gradebook("KPO", "КПО")
    book.add_student(Student("S-001", "Студент"))
    book.add_criterion(Criterion("HW", "ДЗ", 10, 1))
    return book


@pytest.mark.parametrize("value", ["", " ", "S 1", "S/1", "S--1", "[red]", "-S", "S_"])
def test_invalid_codes_are_rejected(value):
    with pytest.raises(DomainError):
        normalize_code(value)


def test_codes_and_text_are_normalized():
    student = Student(" s-001 ", " Студент ", " БПИ ")
    assert (student.code, student.name, student.group) == ("S-001", "Студент", "БПИ")
    assert Gradebook(" kpo ", " КПО ").code == "KPO"
    assert Gradebook("KPO", " КПО ").name == "КПО"


@pytest.mark.parametrize("make", [lambda: Student("S", " "), lambda: Criterion("C", "", 10, 1)])
def test_empty_names_are_rejected(make):
    with pytest.raises(DomainError, match="пустым"):
        make()


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "abc", True, None])
def test_non_finite_or_non_numeric_values_are_rejected(value):
    with pytest.raises(DomainError, match="конечное число"):
        decimal_number(value, "Балл")


@pytest.mark.parametrize("maximum,weight", [(0, 1), (-1, 1), (10, 0), (10, -1)])
def test_criterion_requires_positive_maximum_and_weight(maximum, weight):
    with pytest.raises(DomainError, match="больше нуля"):
        Criterion("HW", "ДЗ", maximum, weight)


@pytest.mark.parametrize("value", ["-0.01", "10.01", "12", "NaN", "Infinity"])
def test_score_cannot_leave_criterion_scale(value):
    with pytest.raises(DomainError):
        Score(value, 10)


@pytest.mark.parametrize("value", ["0", "10", "7.25"])
def test_score_accepts_boundaries_and_fractional_values(value):
    score = Score(value, 10)
    assert score.value == Decimal(value)
    assert score.fraction == Decimal(value) / 10


def test_score_requires_positive_scale():
    with pytest.raises(DomainError, match="больше нуля"):
        Score(0, 0)


def test_entity_identity_differs_from_value_object_equality():
    assert Student("S", "Первая запись") == Student("S", "Другое имя")
    assert Student("S", "Имя") != Student("T", "Имя")
    assert Score(8, 10) == Score("8.0", "10.0")
    assert Score(8, 10) != Score(8, 100)
    assert Criterion("HW", "ДЗ", 10, 30) == Criterion("HW", "Домашняя работа", 20, 50)


def test_entities_and_scores_do_not_allow_external_mutation(book):
    student = book.students[0]
    with pytest.raises(FrozenInstanceError):
        student.name = "Другое имя"
    score = Score(7, 10)
    with pytest.raises(FrozenInstanceError):
        score.value = Decimal(12)
    students = (*book.students, Student("OTHER", "Другой"))
    assert len(students) == 2
    assert len(book.students) == 1


def test_duplicate_student_and_criterion_leave_original_unchanged(book):
    with pytest.raises(DuplicateError):
        book.add_student(Student("s-001", "Другое имя"))
    with pytest.raises(DuplicateError):
        book.add_criterion(Criterion("hw", "Другое ДЗ", 20, 2))
    assert book.student("S-001").name == "Студент"
    assert book.criterion("HW").max_score == 10


@pytest.mark.parametrize("student,criterion", [("UNKNOWN", "HW"), ("S-001", "UNKNOWN")])
def test_aggregate_requires_student_and_criterion_from_gradebook(book, student, criterion):
    with pytest.raises(NotFoundError):
        book.record_evaluation(student, criterion, 5)
    assert book.evaluations_for("S-001") == ()


def test_evaluation_cannot_claim_a_different_scale(book):
    with pytest.raises(DomainError, match="Шкала"):
        Evaluation("S-001", book.criterion("HW"), Score(12, 20))


def test_evaluation_lifecycle_preserves_invariants(book):
    original = book.record_evaluation("s-001", "hw", "7.5", " первая ")
    assert original.comment == "первая"
    with pytest.raises(DuplicateError):
        book.record_evaluation("S-001", "HW", 10)
    with pytest.raises(DomainError):
        book.correct_evaluation("S-001", "HW", 12)
    assert book.evaluation("S-001", "HW").score.value == Decimal("7.5")
    corrected = book.correct_evaluation("S-001", "HW", 10)
    assert corrected == original
    assert corrected.score.value == 10
    assert len(book.evaluations_for("S-001")) == 1
    book.cancel_evaluation("S-001", "HW")
    assert book.evaluations_for("S-001") == ()
    with pytest.raises(NotFoundError):
        book.cancel_evaluation("S-001", "HW")


def test_correction_requires_existing_evaluation(book):
    with pytest.raises(NotFoundError, match="не выставлена"):
        book.correct_evaluation("S-001", "HW", 7)


def test_factory_takes_student_and_criterion_only_from_its_gradebook(book):
    evaluation = book.record_evaluation("s-001", "hw", 8)
    assert evaluation.criterion is book.criterion("HW")
    assert evaluation.score == Score(8, book.criterion("HW").max_score)
    corrected = book.correct_evaluation("S-001", "HW", 9)
    assert corrected.criterion is book.criterion("HW")
