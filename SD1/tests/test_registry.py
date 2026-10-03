"""Реестр имущества на балансе."""

import pytest

from tests.builders import helmet, scooter
from vyshkat.domain import DuplicateInventoryNumberError
from vyshkat.services import AssetRegistry


def test_empty_registry_has_no_assets():
    registry = AssetRegistry()

    assert registry.all() == []
    assert len(registry) == 0


def test_added_assets_are_returned_in_order_of_intake():
    registry = AssetRegistry()
    first, second = scooter("VK-TS-001"), helmet("VK-H-001")

    registry.add(first)
    registry.add(second)

    assert registry.all() == [first, second]
    assert len(registry) == 2


def test_contains_ignores_case_and_spaces():
    registry = AssetRegistry()
    registry.add(scooter("VK-TS-001"))

    assert registry.contains(" vk-ts-001 ")
    assert not registry.contains("VK-TS-002")


def test_same_inventory_number_cannot_be_registered_twice():
    registry = AssetRegistry()
    registry.add(scooter("VK-TS-001"))

    with pytest.raises(DuplicateInventoryNumberError, match="VK-TS-001"):
        registry.add(helmet("vk-ts-001"))


def test_all_returns_a_copy_that_cannot_corrupt_the_registry():
    registry = AssetRegistry()
    registry.add(scooter())

    registry.all().clear()

    assert len(registry) == 1
