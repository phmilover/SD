"""Доменная модель: инварианты и «способности» объектов на балансе."""

import pytest

from vyshkat.domain import (
    Asset,
    Bicycle,
    ChargingCabinet,
    DockStation,
    DomainError,
    ElectricBike,
    ElectricScooter,
    EnergyConsumer,
    Helmet,
    Inventoried,
    Item,
    TechnicalCondition,
    Transport,
    normalize_inventory_number,
)


class TestTechnicalCondition:
    def test_new_device_has_no_wear_and_no_defects(self):
        condition = TechnicalCondition()

        assert condition.wear_percent == 0
        assert condition.defects == ()

    @pytest.mark.parametrize("wear", [-1, 101])
    def test_wear_outside_0_100_is_rejected(self, wear):
        with pytest.raises(DomainError, match="Износ"):
            TechnicalCondition(wear_percent=wear)

    def test_blank_defects_are_dropped_and_others_trimmed(self):
        condition = TechnicalCondition(defects=("  трещина ", "", "   "))

        assert condition.defects == ("трещина",)

    def test_single_defect_string_is_not_split_into_letters(self):
        assert TechnicalCondition(defects="трещина").defects == ("трещина",)


class TestAssetIdentity:
    def test_inventory_number_is_trimmed_and_upper_cased(self):
        scooter = ElectricScooter("Ninebot G30", " vk-ts-001 ", simplicity=7, daily_energy_kwh=0.4)

        assert scooter.inventory_number == "VK-TS-001"

    @pytest.mark.parametrize("number", ["", "   "])
    def test_inventory_number_is_mandatory(self, number):
        with pytest.raises(DomainError, match="Инвентарный номер обязателен"):
            Helmet("Шлем Urban", number)

    def test_inventory_number_rejects_spaces_and_symbols(self):
        with pytest.raises(DomainError, match="только буквы, цифры и дефис"):
            Helmet("Шлем Urban", "VK 001!")

    def test_number_rules_are_available_before_the_object_is_built(self):
        # Консоль проверяет номер сразу после ввода, по тем же правилам, что и Asset.
        assert normalize_inventory_number(" vk-h-7 ") == "VK-H-7"
        with pytest.raises(DomainError):
            normalize_inventory_number("VK 7")

    def test_name_is_mandatory(self):
        with pytest.raises(DomainError, match="Наименование"):
            Helmet("  ", "VK-H-001")

    def test_condition_defaults_to_new(self):
        helmet = Helmet("Шлем Urban", "VK-H-001")

        assert helmet.condition == TechnicalCondition()

    def test_repr_shows_type_name_and_number_for_debugging(self):
        assert repr(Helmet("Шлем Urban", "VK-H-001")) == "Helmet('Шлем Urban', 'VK-H-001')"


class TestTransport:
    @pytest.mark.parametrize("simplicity", [1, 10])
    def test_simplicity_accepts_bounds_1_and_10(self, simplicity):
        bike = Bicycle("Forward Tracer", "VK-B-001", simplicity=simplicity)

        assert bike.simplicity == simplicity

    @pytest.mark.parametrize("simplicity", [0, 11, 6.5, True])
    def test_simplicity_must_be_a_whole_number_from_1_to_10(self, simplicity):
        with pytest.raises(DomainError, match="Простота"):
            Bicycle("Forward Tracer", "VK-B-001", simplicity=simplicity)

    def test_abstract_transport_cannot_be_created_directly(self):
        with pytest.raises(TypeError):
            Transport("Безымянный", "VK-X-001", simplicity=5)  # type: ignore[abstract]


class TestEnergyConsumers:
    @pytest.mark.parametrize(
        "asset",
        [
            ElectricScooter("Ninebot G30", "VK-TS-001", simplicity=7, daily_energy_kwh=0.4),
            ElectricBike("Eltreco XT", "VK-EB-001", simplicity=5, daily_energy_kwh=0.6),
            DockStation("Док на 10 мест", "VK-D-001", daily_energy_kwh=2.5),
            ChargingCabinet("Шкаф на 12 ячеек", "VK-C-001", daily_energy_kwh=4.0),
        ],
    )
    def test_powered_devices_report_daily_energy(self, asset):
        assert isinstance(asset, EnergyConsumer)
        assert asset.daily_energy_kwh > 0

    @pytest.mark.parametrize(
        "asset",
        [
            Bicycle("Forward Tracer", "VK-B-001", simplicity=8),
            Helmet("Шлем Urban", "VK-H-001"),
        ],
    )
    def test_unpowered_things_are_not_energy_consumers(self, asset):
        # Не «расход = 0», а просто не реализуют интерфейс (ISP/LSP).
        assert not isinstance(asset, EnergyConsumer)

    @pytest.mark.parametrize("energy", [0, -0.5, float("nan"), float("inf")])
    def test_energy_must_be_a_positive_finite_number(self, energy):
        with pytest.raises(DomainError, match="кВт·ч"):
            DockStation("Док", "VK-D-001", daily_energy_kwh=energy)


class TestKindsAndCategories:
    @pytest.mark.parametrize(
        ("kind", "title", "category"),
        [
            (ElectricScooter, "Электросамокат", Transport),
            (ElectricBike, "Электровелосипед", Transport),
            (Bicycle, "Велосипед", Transport),
            (Helmet, "Шлем", Item),
            (DockStation, "Док-станция", Item),
            (ChargingCabinet, "Зарядный шкаф", Item),
        ],
    )
    def test_every_kind_is_an_inventoried_asset_with_title(self, kind, title, category):
        assert issubclass(kind, Asset)
        assert issubclass(kind, Inventoried)
        assert issubclass(kind, category)
        assert kind.kind == title

    def test_categories_have_human_readable_titles(self):
        assert Bicycle.category == "Транспорт"
        assert Helmet.category == "Вещи"
