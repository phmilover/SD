from fractions import Fraction

from pos.application.ports import ResultsExporter
from pos.application.reports import CourseStatistics, StudentResult
from pos.domain.errors import DomainError
from pos.domain.model import Criterion, Evaluation, Gradebook, Student
from pos.domain.ports import GradebookRepository
from pos.domain.scoring import FinalScoreService
from pos.domain.values import Number, round_hundredths


class PosFacade:
    """Фасад: UI не управляет снимками репозитория, расчётом и экспортом."""

    def __init__(
        self,
        repository: GradebookRepository,
        scores: FinalScoreService,
        exporter: ResultsExporter,
    ) -> None:
        self._repository = repository
        self._scores = scores
        self._exporter = exporter

    @property
    def policy_name(self) -> str:
        return self._scores.policy_name

    def add_student(self, code: str, name: str, group: str = "") -> Student:
        gradebook = self._repository.load()
        student = Student(code, name, group)
        gradebook.add_student(student)
        self._repository.save(gradebook)
        return student

    def add_criterion(self, code: str, name: str, maximum: Number, weight: Number) -> Criterion:
        gradebook = self._repository.load()
        criterion = Criterion(code, name, maximum, weight)
        gradebook.add_criterion(criterion)
        self._repository.save(gradebook)
        return criterion

    def students(self) -> tuple[Student, ...]:
        return self._repository.load().students

    def criteria(self) -> tuple[Criterion, ...]:
        return self._repository.load().criteria

    def evaluate(
        self, student: str, criterion: str, value: Number, comment: str = ""
    ) -> Evaluation:
        gradebook = self._repository.load()
        evaluation = gradebook.record_evaluation(student, criterion, value, comment)
        self._repository.save(gradebook)
        return evaluation

    def correct(self, student: str, criterion: str, value: Number, comment: str = "") -> Evaluation:
        gradebook = self._repository.load()
        evaluation = gradebook.correct_evaluation(student, criterion, value, comment)
        self._repository.save(gradebook)
        return evaluation

    def cancel(self, student: str, criterion: str) -> None:
        gradebook = self._repository.load()
        gradebook.cancel_evaluation(student, criterion)
        self._repository.save(gradebook)

    def evaluations(self, student: str) -> tuple[Evaluation, ...]:
        return self._repository.load().evaluations_for(student)

    def result(self, student: str) -> StudentResult:
        gradebook = self._repository.load()
        return StudentResult(gradebook.student(student), self._scores.calculate(gradebook, student))

    def results(self) -> tuple[StudentResult, ...]:
        return self._results(self._repository.load())

    def _results(self, gradebook: Gradebook) -> tuple[StudentResult, ...]:
        return tuple(
            StudentResult(student, self._scores.calculate(gradebook, student.code))
            for student in gradebook.students
        )

    def statistics(self) -> CourseStatistics:
        gradebook = self._repository.load()
        finals = [row.final for row in self._results(gradebook)]
        values = [f.value for f in finals]
        return CourseStatistics(
            students=len(gradebook.students),
            criteria=len(gradebook.criteria),
            evaluations=sum(f.assessed for f in finals),
            complete_students=sum(f.complete for f in finals),
            average=round_hundredths(sum(map(Fraction, values), Fraction(0)) / len(values))
            if values
            else None,
            minimum=min(values) if values else None,
            maximum=max(values) if values else None,
        )

    def export(self, destination: str) -> int:
        gradebook = self._repository.load()
        if not gradebook.criteria:
            raise DomainError("Нельзя экспортировать итог: рубрикатор пуст")
        results = self._results(gradebook)
        self._exporter.export(results, destination)
        return len(results)
