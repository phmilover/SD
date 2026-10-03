"""Приёмка техники: техосмотр подменяется через DI-контейнер (fake / mock)."""

from unittest.mock import create_autospec

import pytest

from tests.builders import helmet, scooter
from tests.fakes import approving_service_center, rejecting_service_center
from vyshkat.domain import DuplicateInventoryNumberError
from vyshkat.services import InspectionResult, ServiceCenter


def test_device_approved_by_service_center_is_put_on_balance(container):
    container.service_center.override(approving_service_center())
    device = scooter()

    result = container.intake().receive(device)

    assert result.approved
    assert container.registry().all() == [device]


def test_device_rejected_by_service_center_stays_off_balance(container):
    container.service_center.override(rejecting_service_center("Люфт руля"))

    result = container.intake().receive(scooter())

    assert not result.approved
    assert result.reasons == ("Люфт руля",)
    assert len(container.registry()) == 0


def test_every_new_device_goes_through_inspection(container):
    fake = approving_service_center()
    container.service_center.override(fake)
    device = helmet()

    container.intake().receive(device)

    assert fake.inspected == [device]


def test_duplicate_number_is_refused_before_inspection(container):
    fake = approving_service_center()
    container.service_center.override(fake)
    intake = container.intake()
    intake.receive(scooter("VK-TS-001"))

    with pytest.raises(DuplicateInventoryNumberError):
        intake.receive(helmet("VK-TS-001"))

    assert len(fake.inspected) == 1  # второй объект на осмотр даже не попал


def test_service_center_can_be_replaced_with_a_mock(container):
    mock = create_autospec(ServiceCenter, instance=True)
    mock.inspect.return_value = InspectionResult.reject("Нет документов")
    container.service_center.override(mock)
    device = scooter()

    result = container.intake().receive(device)

    mock.inspect.assert_called_once_with(device)
    assert result.reasons == ("Нет документов",)


def test_without_override_the_real_inspection_policy_is_used(container):
    intake = container.intake()

    assert intake.receive(scooter("VK-1", wear=10)).approved
    assert not intake.receive(scooter("VK-2", wear=90)).approved
    assert [a.inventory_number for a in container.registry().all()] == ["VK-1"]


def test_number_can_be_checked_before_the_device_is_built(container):
    intake = container.intake()
    intake.receive(scooter("VK-TS-001"))

    intake.ensure_number_is_free("VK-TS-002")
    with pytest.raises(DuplicateInventoryNumberError):
        intake.ensure_number_is_free("VK-TS-001")
