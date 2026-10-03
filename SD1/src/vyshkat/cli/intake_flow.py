"""Общий для меню и демо сценарий «создать → техосмотр → показать итог»."""

from collections.abc import Callable

from vyshkat.cli.view import FleetView
from vyshkat.domain import Asset, DomainError
from vyshkat.services import IntakeService


def receive_and_show(intake: IntakeService, view: FleetView, build: Callable[[], Asset]) -> None:
    """Ошибки предметной области показываются пользователю, а не роняют программу."""
    try:
        asset = build()
        result = intake.receive(asset)
    except DomainError as error:
        view.error(str(error))
        return
    view.inspection(asset, result)
