"""Composition root: единственное место, где выбираются конкретные реализации и пороги."""

from dependency_injector import containers, providers
from rich.console import Console

from vyshkat.catalog import ASSET_KINDS
from vyshkat.cli.app import ConsoleApp
from vyshkat.cli.demo import DemoScenario
from vyshkat.cli.prompter import Prompter
from vyshkat.cli.view import FleetView
from vyshkat.services import (
    AssetRegistry,
    FleetReports,
    IntakeService,
    NoviceRule,
    StandardServiceCenter,
)


class Container(containers.DeclarativeContainer):
    # --- предметная область -------------------------------------------------
    registry = providers.Singleton(AssetRegistry)

    # Тесты подменяют техосмотр: container.service_center.override(fake)
    service_center = providers.Singleton(StandardServiceCenter, max_wear_percent=30)
    novice_rule = providers.Singleton(NoviceRule, min_simplicity=6, max_wear_percent=20)

    intake = providers.Singleton(IntakeService, registry=registry, service_center=service_center)
    reports = providers.Singleton(FleetReports, registry=registry, novice_rule=novice_rule)

    # --- консоль ------------------------------------------------------------
    console = providers.Singleton(Console)
    view = providers.Singleton(FleetView, console=console)
    prompter = providers.Singleton(Prompter, console=console)

    demo = providers.Factory(DemoScenario, intake=intake, reports=reports, view=view)
    # `demo` для пункта меню передаётся при вызове: container.app(demo=...)
    app = providers.Factory(
        ConsoleApp,
        intake=intake,
        reports=reports,
        view=view,
        prompter=prompter,
        catalog=providers.Object(ASSET_KINDS),
    )
