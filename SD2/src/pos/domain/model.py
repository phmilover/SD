from dataclasses import dataclass, field
from decimal import Decimal

from pos.domain.errors import DomainError, DuplicateError, NotFoundError
from pos.domain.values import Number, Score, clean_text, decimal_number, normalize_code


@dataclass(frozen=True)
class Student:
    code: str
    name: str = field(compare=False)
    group: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", normalize_code(self.code))
        object.__setattr__(self, "name", clean_text(self.name, "Имя студента"))
        object.__setattr__(self, "group", clean_text(self.group, "Группа", required=False))


@dataclass(frozen=True)
class Criterion:
    code: str
    name: str = field(compare=False)
    max_score: Decimal = field(compare=False)
    weight: Decimal = field(compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", normalize_code(self.code))
        object.__setattr__(self, "name", clean_text(self.name, "Название критерия"))
        maximum = decimal_number(self.max_score, "Максимальный балл")
        weight = decimal_number(self.weight, "Вес")
        if maximum <= 0 or weight <= 0:
            raise DomainError("Максимальный балл и вес должны быть больше нуля")
        object.__setattr__(self, "max_score", maximum)
        object.__setattr__(self, "weight", weight)


@dataclass(frozen=True)
class Evaluation:
    """Идентичность — пара студент/критерий; исправление заменяет состояние оценки."""

    student_code: str
    criterion: Criterion
    score: Score = field(compare=False)
    comment: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "student_code", normalize_code(self.student_code))
        if self.score.maximum != self.criterion.max_score:
            raise DomainError("Шкала оценки должна совпадать с максимумом критерия")
        object.__setattr__(self, "comment", clean_text(self.comment, "Комментарий", required=False))


class Gradebook:
    """Корень агрегата: состав курса, рубрикатор и оценки меняются только вместе."""

    def __init__(self, code: str, name: str) -> None:
        self._code = normalize_code(code)
        self._name = clean_text(name, "Название курса")
        self._students: dict[str, Student] = {}
        self._criteria: dict[str, Criterion] = {}
        self._evaluations: dict[str, dict[str, Evaluation]] = {}

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def students(self) -> tuple[Student, ...]:
        return tuple(self._students.values())

    @property
    def criteria(self) -> tuple[Criterion, ...]:
        return tuple(self._criteria.values())

    def student(self, code: str) -> Student:
        code = normalize_code(code)
        try:
            return self._students[code]
        except KeyError as error:
            raise NotFoundError(f"Студент {code} не найден") from error

    def criterion(self, code: str) -> Criterion:
        code = normalize_code(code)
        try:
            return self._criteria[code]
        except KeyError as error:
            raise NotFoundError(f"Критерий {code} не найден в рубрикаторе") from error

    def add_student(self, student: Student) -> None:
        if student.code in self._students:
            raise DuplicateError(f"Студент {student.code} уже существует")
        self._students[student.code] = student
        self._evaluations[student.code] = {}

    def add_criterion(self, criterion: Criterion) -> None:
        if criterion.code in self._criteria:
            raise DuplicateError(f"Критерий {criterion.code} уже существует")
        self._criteria[criterion.code] = criterion

    def evaluation(self, student_code: str, criterion_code: str) -> Evaluation:
        student = self.student(student_code)
        criterion = self.criterion(criterion_code)
        try:
            return self._evaluations[student.code][criterion.code]
        except KeyError as error:
            raise NotFoundError("Оценка ещё не выставлена") from error

    def evaluations_for(self, student_code: str) -> tuple[Evaluation, ...]:
        student = self.student(student_code)
        return tuple(self._evaluations[student.code].values())

    def record_evaluation(
        self,
        student_code: str,
        criterion_code: str,
        value: Number,
        comment: str = "",
    ) -> Evaluation:
        evaluation = self._create_evaluation(student_code, criterion_code, value, comment)
        evaluations = self._evaluations[evaluation.student_code]
        if evaluation.criterion.code in evaluations:
            raise DuplicateError("Оценка уже выставлена; используйте исправление")
        evaluations[evaluation.criterion.code] = evaluation
        return evaluation

    def correct_evaluation(
        self,
        student_code: str,
        criterion_code: str,
        value: Number,
        comment: str = "",
    ) -> Evaluation:
        self.evaluation(student_code, criterion_code)
        evaluation = self._create_evaluation(student_code, criterion_code, value, comment)
        self._evaluations[evaluation.student_code][evaluation.criterion.code] = evaluation
        return evaluation

    def cancel_evaluation(self, student_code: str, criterion_code: str) -> None:
        evaluation = self.evaluation(student_code, criterion_code)
        del self._evaluations[evaluation.student_code][evaluation.criterion.code]

    def _create_evaluation(
        self, student_code: str, criterion_code: str, value: Number, comment: str
    ) -> Evaluation:
        """Фабрика: единственное место, где создаётся оценка ведомости.

        Студент и критерий берутся только из этой ведомости, балл — в шкале критерия.
        """
        student = self.student(student_code)
        criterion = self.criterion(criterion_code)
        return Evaluation(student.code, criterion, Score(value, criterion.max_score), comment)
