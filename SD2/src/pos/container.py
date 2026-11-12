"""Composition root: конкретные адаптеры и правило итога выбираются только здесь."""

from dependency_injector import containers, providers
from rich.console import Console

from pos.adapters.csv_export import CsvResultsExporter
from pos.adapters.memory import InMemoryGradebookRepository
from pos.application.facade import PosFacade
from pos.cli.app import ConsoleApp
from pos.cli.demo import DemoScenario
from pos.cli.prompter import Prompter
from pos.cli.view import PosView
from pos.domain.model import Gradebook
from pos.domain.scoring import AssessedOnly, FinalScoreService, WeightedAverage


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(default={"policy": "weighted"})
    initial_gradebook = providers.Factory(
        Gradebook, code="KPO", name="Конструирование программного обеспечения"
    )
    repository = providers.Singleton(InMemoryGradebookRepository, initial=initial_gradebook)
    scoring_strategy = providers.Selector(
        config.policy,
        weighted=providers.Singleton(WeightedAverage),
        assessed=providers.Singleton(AssessedOnly),
    )
    scores = providers.Singleton(FinalScoreService, strategy=scoring_strategy)
    exporter = providers.Singleton(CsvResultsExporter)
    facade = providers.Singleton(
        PosFacade,
        repository=repository,
        scores=scores,
        exporter=exporter,
    )
    console = providers.Singleton(Console)
    prompter = providers.Singleton(Prompter, console=console)
    view = providers.Singleton(PosView, console=console)
    demo = providers.Factory(DemoScenario, facade=facade, view=view)
    app = providers.Factory(ConsoleApp, facade=facade, prompter=prompter, view=view)
