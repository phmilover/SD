"""Реальная политика техосмотра StandardServiceCenter."""

import pytest

from tests.builders import bicycle, helmet, scooter
from vyshkat.services import InspectionResult, StandardServiceCenter


@pytest.fixture
def service_center() -> StandardServiceCenter:
    return StandardServiceCenter(max_wear_percent=30)


def test_new_device_without_defects_is_approved(service_center):
    result = service_center.inspect(scooter(wear=0))

    assert result == InspectionResult.approve()
    assert result.approved
    assert result.reasons == ()


def test_wear_exactly_at_limit_is_still_approved(service_center):
    assert service_center.inspect(bicycle(wear=30)).approved


def test_wear_above_limit_is_rejected_with_reason(service_center):
    result = service_center.inspect(bicycle(wear=31))

    assert not result.approved
    assert result.reasons == ("Износ 31% превышает допустимые 30%",)


def test_every_defect_becomes_a_rejection_reason(service_center):
    result = service_center.inspect(helmet(defects=("трещина корпуса", "порван ремешок")))

    assert not result.approved
    assert result.reasons == ("Дефект: трещина корпуса", "Дефект: порван ремешок")


def test_all_problems_are_reported_at_once(service_center):
    result = service_center.inspect(scooter(wear=80, defects=("не работает тормоз",)))

    assert len(result.reasons) == 2


def test_wear_limit_is_configurable():
    strict = StandardServiceCenter(max_wear_percent=10)

    assert not strict.inspect(bicycle(wear=15)).approved


def test_invalid_wear_limit_is_rejected():
    with pytest.raises(ValueError):
        StandardServiceCenter(max_wear_percent=120)


def test_reject_requires_at_least_one_reason():
    with pytest.raises(ValueError):
        InspectionResult.reject()
