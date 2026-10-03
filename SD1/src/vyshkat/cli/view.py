"""Отображение результатов в консоли (rich). Никакой бизнес-логики — только вывод."""

from collections.abc import Sequence

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from vyshkat.domain import Asset, EnergyConsumer, Inventoried, Transport
from vyshkat.services import FleetSummary, InspectionResult, NoviceAssessment


class FleetView:
    def __init__(self, console: Console) -> None:
        self._console = console

    # --- общие элементы ---------------------------------------------------

    def banner(self) -> None:
        title = "[bold magenta]ВышКат[/] · учёт парка кикшеринга ВШЭ"
        slogan = "[italic]«Доедем до дедлайна»[/]"
        self._console.print(Panel.fit(f"{title}\n{slogan}", border_style="magenta"))

    def menu(self, titles: Sequence[str]) -> None:
        table = Table(show_header=False, box=None, padding=(0, 1))
        for number, title in enumerate(titles, start=1):
            table.add_row(f"[bold cyan]{number}[/]", escape(title))
        table.add_row("[bold cyan]0[/]", "Выход")
        self._console.print()
        self._console.print(Panel(table, title="Меню", title_align="left", expand=False))

    def section(self, title: str) -> None:
        self._console.print()
        self._console.print(Rule(f"[bold]{escape(title)}[/]", align="left", style="magenta"))

    def note(self, text: str) -> None:
        self._console.print(f"[dim]{escape(text)}[/]")

    def error(self, message: str) -> None:
        self._console.print(f"[bold red]✖ Ошибка:[/] {escape(message)}")

    def goodbye(self) -> None:
        self._console.print("\n[magenta]До встречи! Доедем до дедлайна.[/]")

    # --- приёмка ----------------------------------------------------------

    def inspection(self, asset: Asset, result: InspectionResult) -> None:
        if result.approved:
            status, style, extra = "[bold green]✔ Принято на баланс[/]", "green", ""
        else:
            reasons = "\n".join(f"  • {escape(reason)}" for reason in result.reasons)
            status, style, extra = "[bold red]✖ Отказ техосмотра[/]", "red", f"\n{reasons}"
        body = f"{status}: {self._title(asset)}\n[dim]{self._details(asset)}[/]{extra}"
        self._console.print(Panel(body, border_style=style, expand=False))

    # --- отчёты -----------------------------------------------------------

    def summary(self, summary: FleetSummary) -> None:
        self._heading("Парк «ВышКат»: единицы и энергопотребление")
        if summary.by_kind:
            table = Table(box=box.ROUNDED, header_style="bold")
            table.add_column("Вид")
            table.add_column("Категория")
            table.add_column("Ед.", justify="right")
            table.add_column("кВт·ч/сут", justify="right")
            for stats in summary.by_kind:
                energy = "—" if stats.daily_energy_kwh is None else f"{stats.daily_energy_kwh:.2f}"
                table.add_row(stats.kind, stats.category, str(stats.units), energy)
            self._console.print(table)
        else:
            self.note("Парк пока пуст.")
        counters = [
            f"{category}: [bold]{units}[/]" for category, units in summary.units_by_category.items()
        ]
        counters.append(f"Всего единиц: [bold]{summary.total_units}[/]")
        self._console.print(" · ".join(counters))
        self._console.print(
            f"Суммарное потребление: [bold]{summary.total_daily_energy_kwh:.2f} кВт·ч/сут[/]"
        )

    def novices(self, assessments: Sequence[NoviceAssessment], rule_description: str) -> None:
        self._heading(f"Техника для новичков (правило: {rule_description})")
        suitable = [a.transport for a in assessments if a.suitable]
        unsuitable = [a for a in assessments if not a.suitable]

        self._console.print(f"[bold green]Можно выдавать новичкам: {len(suitable)}[/]")
        if suitable:
            table = self._transport_table()
            for transport in suitable:
                table.add_row(*self._transport_row(transport))
            self._console.print(table)

        if unsuitable:
            self._console.print(f"[bold yellow]Не для новичков: {len(unsuitable)}[/]")
            table = Table(box=box.ROUNDED, header_style="bold")
            table.add_column("Инв. номер", style="bold cyan", no_wrap=True)
            table.add_column("Вид")
            table.add_column("Наименование")
            table.add_column("Почему")
            for assessment in unsuitable:
                transport = assessment.transport
                table.add_row(
                    transport.inventory_number,
                    transport.kind,
                    escape(transport.name),
                    escape("; ".join(assessment.reasons_against)),
                )
            self._console.print(table)

    def inventory(self, entries: Sequence[Inventoried]) -> None:
        self._heading(f"Инвентарная ведомость ({len(entries)} поз.)")
        if not entries:
            self.note("На балансе ничего нет.")
            return
        table = Table(box=box.ROUNDED, header_style="bold")
        table.add_column("№", justify="right", style="dim")
        table.add_column("Инв. номер", style="bold cyan", no_wrap=True)
        table.add_column("Наименование")
        table.add_column("Вид")
        for number, entry in enumerate(entries, start=1):
            table.add_row(str(number), entry.inventory_number, escape(entry.name), entry.kind)
        self._console.print(table)

    # --- вспомогательное --------------------------------------------------

    def _heading(self, text: str) -> None:
        self._console.print(f"\n[bold underline]{escape(text)}[/]")

    @staticmethod
    def _title(asset: Asset) -> str:
        return f"{asset.kind} «{escape(asset.name)}», {asset.inventory_number}"

    @staticmethod
    def _details(asset: Asset) -> str:
        parts = []
        if isinstance(asset, Transport):
            parts.append(f"простота {asset.simplicity}/10")
        if isinstance(asset, EnergyConsumer):
            parts.append(f"{asset.daily_energy_kwh:.2f} кВт·ч/сут")
        parts.append(f"износ {asset.condition.wear_percent}%")
        return " · ".join(parts)

    @staticmethod
    def _transport_table() -> Table:
        table = Table(box=box.ROUNDED, header_style="bold")
        table.add_column("Инв. номер", style="bold cyan", no_wrap=True)
        table.add_column("Вид")
        table.add_column("Наименование")
        table.add_column("Простота", justify="right")
        table.add_column("Износ", justify="right")
        return table

    @staticmethod
    def _transport_row(transport: Transport) -> tuple[str, ...]:
        return (
            transport.inventory_number,
            transport.kind,
            escape(transport.name),
            f"{transport.simplicity}/10",
            f"{transport.condition.wear_percent}%",
        )
