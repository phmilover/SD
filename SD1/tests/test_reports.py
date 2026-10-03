"""Отчёты по парку: единицы, энергия, новички, инвентарная ведомость."""

import pytest

from tests.builders import bicycle, cabinet, dock, ebike, helmet, scooter
from vyshkat.services import AssetRegistry, FleetReports, KindStats, NoviceRule


def make_reports(*assets) -> FleetReports:
    registry = AssetRegistry()
    for asset in assets:
        registry.add(asset)
    return FleetReports(registry, NoviceRule(min_simplicity=6, max_wear_percent=20))


class TestSummary:
    def test_empty_park_has_zero_units_and_energy(self):
        summary = make_reports().summary()

        assert summary.total_units == 0
        assert summary.units_by_category == {}
        assert summary.total_daily_energy_kwh == 0
        assert summary.by_kind == ()

    def test_units_are_counted_by_category(self):
        summary = make_reports(scooter("VK-1"), bicycle("VK-2"), helmet("VK-3")).summary()

        assert summary.units_by_category == {"Транспорт": 2, "Вещи": 1}
        assert summary.total_units == 3

    def test_energy_is_summed_over_transport_and_equipment(self):
        reports = make_reports(
            scooter("VK-1", energy=0.4),
            scooter("VK-2", energy=0.35),
            ebike("VK-3", energy=0.6),
            dock("VK-4", energy=2.5),
            cabinet("VK-5", energy=4.0),
            bicycle("VK-6"),
            helmet("VK-7"),
        )

        assert reports.total_daily_energy_kwh() == pytest.approx(7.85)
        assert reports.summary().total_daily_energy_kwh == pytest.approx(7.85)

    def test_stats_are_grouped_by_kind_in_order_of_first_intake(self):
        summary = make_reports(
            scooter("VK-1", energy=0.4),
            helmet("VK-2"),
            scooter("VK-3", energy=0.5),
        ).summary()

        assert summary.by_kind == (
            KindStats("Электросамокат", "Транспорт", units=2, daily_energy_kwh=pytest.approx(0.9)),
            KindStats("Шлем", "Вещи", units=1, daily_energy_kwh=None),
        )


class TestNovices:
    def test_only_suitable_transport_is_listed_for_novices(self):
        easy = scooter("VK-1", simplicity=8)
        hard = ebike("VK-2", simplicity=4)
        worn = bicycle("VK-3", simplicity=9, wear=25)
        reports = make_reports(easy, hard, worn, helmet("VK-4"))

        suitable = [a.transport for a in reports.novice_assessments() if a.suitable]

        assert suitable == [easy]

    def test_assessments_cover_transport_only(self):
        reports = make_reports(scooter("VK-1"), helmet("VK-2"), dock("VK-3"))

        assert [a.transport.inventory_number for a in reports.novice_assessments()] == ["VK-1"]

    def test_rule_description_is_exposed_for_the_report_header(self):
        assert make_reports().novice_rule_description() == "простота ≥ 6 и износ ≤ 20%"


class TestInventory:
    def test_inventory_lists_transport_and_items_sorted_by_number(self):
        reports = make_reports(helmet("VK-H-001"), scooter("VK-TS-002"), dock("VK-D-001"))

        numbers = [asset.inventory_number for asset in reports.inventory()]

        assert numbers == ["VK-D-001", "VK-H-001", "VK-TS-002"]
