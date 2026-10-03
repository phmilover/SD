"""Правило допуска транспорта для новичков."""

from dataclasses import dataclass

from vyshkat.domain import Transport


@dataclass(frozen=True)
class NoviceAssessment:
    transport: Transport
    reasons_against: tuple[str, ...]

    @property
    def suitable(self) -> bool:
        return not self.reasons_against


class NoviceRule:
    """База из ТЗ — «простота» ≥ 6; усложнение — новичкам не выдаём изношенную технику.

    Пороги задаются в DI-контейнере. Интерфейс не выделен: вариант правила один (YAGNI).
    """

    def __init__(self, min_simplicity: int = 6, max_wear_percent: int = 100) -> None:
        if not Transport.MIN_SIMPLICITY <= min_simplicity <= Transport.MAX_SIMPLICITY:
            raise ValueError("Порог простоты должен быть в пределах шкалы 1–10")
        if not 0 <= max_wear_percent <= 100:
            raise ValueError("Порог износа должен быть в диапазоне 0–100%")
        self._min_simplicity = min_simplicity
        self._max_wear_percent = max_wear_percent

    def assess(self, transport: Transport) -> NoviceAssessment:
        reasons: list[str] = []
        if transport.simplicity < self._min_simplicity:
            reasons.append(f"простота {transport.simplicity} < {self._min_simplicity}")
        wear = transport.condition.wear_percent
        if wear > self._max_wear_percent:
            reasons.append(f"износ {wear}% > {self._max_wear_percent}%")
        return NoviceAssessment(transport, tuple(reasons))

    def describe(self) -> str:
        return f"простота ≥ {self._min_simplicity} и износ ≤ {self._max_wear_percent}%"
