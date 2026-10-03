"""Правило «можно выдавать новичку»: простота ≥ 6 и износ ≤ 20%."""

import pytest

from tests.builders import bicycle, scooter
from vyshkat.services import NoviceRule


@pytest.fixture
def rule() -> NoviceRule:
    return NoviceRule(min_simplicity=6, max_wear_percent=20)


@pytest.mark.parametrize(("simplicity", "suitable"), [(5, False), (6, True), (10, True)])
def test_simplicity_threshold_is_six_inclusive(rule, simplicity, suitable):
    assessment = rule.assess(scooter(simplicity=simplicity))

    assert assessment.suitable is suitable


@pytest.mark.parametrize(("wear", "suitable"), [(20, True), (21, False)])
def test_worn_transport_is_not_given_to_novices(rule, wear, suitable):
    assert rule.assess(bicycle(simplicity=9, wear=wear)).suitable is suitable


def test_assessment_explains_every_reason(rule):
    assessment = rule.assess(bicycle(simplicity=3, wear=25))

    assert assessment.reasons_against == (
        "простота 3 < 6",
        "износ 25% > 20%",
    )


def test_assessment_keeps_the_transport(rule):
    transport = scooter()

    assert rule.assess(transport).transport is transport


def test_rule_describes_itself_for_reports(rule):
    assert rule.describe() == "простота ≥ 6 и износ ≤ 20%"


def test_base_rule_from_assignment_is_the_default():
    assert NoviceRule().assess(scooter(simplicity=6, wear=0)).suitable
    assert not NoviceRule().assess(scooter(simplicity=5, wear=0)).suitable


@pytest.mark.parametrize(
    "thresholds",
    [{"min_simplicity": 0}, {"min_simplicity": 11}, {"max_wear_percent": 101}],
)
def test_thresholds_outside_the_scales_are_rejected(thresholds):
    with pytest.raises(ValueError):
        NoviceRule(**thresholds)
