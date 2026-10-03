"""Сборка зависимостей в DI-контейнере."""

from tests.builders import scooter
from tests.fakes import approving_service_center
from vyshkat.services import StandardServiceCenter


def test_real_service_center_is_wired_by_default(container):
    assert isinstance(container.service_center(), StandardServiceCenter)


def test_intake_and_reports_share_one_registry(container):
    container.intake().receive(scooter())

    assert container.reports().summary().total_units == 1


def test_services_are_singletons_within_one_container(container):
    assert container.intake() is container.intake()
    assert container.registry() is container.registry()


def test_override_is_temporary_when_used_as_context_manager(container):
    fake = approving_service_center()

    with container.service_center.override(fake):
        assert container.service_center() is fake

    assert isinstance(container.service_center(), StandardServiceCenter)


def test_container_applies_the_stricter_novice_rule(container):
    assert container.reports().novice_rule_description() == "простота ≥ 6 и износ ≤ 20%"
