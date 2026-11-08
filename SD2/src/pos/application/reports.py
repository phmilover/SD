from dataclasses import dataclass
from decimal import Decimal

from pos.domain.model import Student
from pos.domain.scoring import FinalScore


@dataclass(frozen=True)
class StudentResult:
    student: Student
    final: FinalScore


@dataclass(frozen=True)
class CourseStatistics:
    students: int
    criteria: int
    evaluations: int
    complete_students: int
    average: Decimal | None
    minimum: Decimal | None
    maximum: Decimal | None
