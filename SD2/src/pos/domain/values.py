import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from pos.domain.errors import DomainError

Number = Decimal | int | str
_CODE = re.compile(r"[A-ZА-ЯЁ0-9]+(?:[-_][A-ZА-ЯЁ0-9]+)*")
_MAX_EXPONENT = 9


def clean_text(value: str, label: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise DomainError(f"{label}: требуется строка")
    value = value.strip()
    if required and not value:
        raise DomainError(f"{label}: значение не может быть пустым")
    return value


def normalize_code(value: str) -> str:
    value = clean_text(value, "Код").upper()
    if not _CODE.fullmatch(value):
        raise DomainError("Код: только буквы, цифры, дефис и подчёркивание, например S-001")
    return value


def decimal_number(value: Number, label: str) -> Decimal:
    """Число без двоичной погрешности: float и bool не принимаются."""
    if isinstance(value, bool) or not isinstance(value, Decimal | int | str):
        raise DomainError(f"{label}: требуется конечное число")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise DomainError(f"{label}: требуется конечное число") from error
    if not result.is_finite():
        raise DomainError(f"{label}: требуется конечное число")
    if result.is_zero():
        return Decimal(0)
    # Ограничение порядка не даёт записи вроде 1e999999999 построить огромную дробь.
    if abs(result.adjusted()) > _MAX_EXPONENT:
        raise DomainError(f"{label}: число должно быть от 1e-9 до 1e9 по модулю")
    return Decimal(format(result.normalize(), "f"))


def round_hundredths(value: Fraction) -> Decimal:
    """Half-up без промежуточной погрешности и зависимости от decimal.getcontext()."""
    magnitude = abs(value)
    units, remainder = divmod(magnitude.numerator * 100, magnitude.denominator)
    if 2 * remainder >= magnitude.denominator:
        units += 1
    sign = "-" if value < 0 else ""
    return Decimal(f"{sign}{units // 100}.{units % 100:02d}")


@dataclass(frozen=True)
class Score:
    """Значение и шкала неразделимы: 8/10 и 8/100 — разные баллы."""

    value: Decimal
    maximum: Decimal

    def __post_init__(self) -> None:
        value = decimal_number(self.value, "Балл")
        maximum = decimal_number(self.maximum, "Максимальный балл")
        if maximum <= 0:
            raise DomainError("Максимальный балл должен быть больше нуля")
        if not 0 <= value <= maximum:
            raise DomainError(f"Балл должен быть от 0 до {maximum}")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "maximum", maximum)

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.value) / Fraction(self.maximum)
