"""Тестовые двойники, которые подставляются через DI-контейнер."""

from vyshkat.domain import Asset
from vyshkat.services import InspectionResult, ServiceCenter


class FakeServiceCenter(ServiceCenter):
    """Stub + spy: выносит заранее заданное решение и запоминает, что осматривал."""

    def __init__(self, result: InspectionResult) -> None:
        self.result = result
        self.inspected: list[Asset] = []

    def inspect(self, asset: Asset) -> InspectionResult:
        self.inspected.append(asset)
        return self.result


def approving_service_center() -> FakeServiceCenter:
    return FakeServiceCenter(InspectionResult.approve())


def rejecting_service_center(*reasons: str) -> FakeServiceCenter:
    return FakeServiceCenter(InspectionResult.reject(*(reasons or ("Не прошёл осмотр",))))
