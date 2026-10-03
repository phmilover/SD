"""Прикладные сервисы: техосмотр, реестр, приёмка, правило для новичков, отчёты."""

from vyshkat.services.intake import IntakeService
from vyshkat.services.novice_rule import NoviceAssessment, NoviceRule
from vyshkat.services.registry import AssetRegistry
from vyshkat.services.reports import FleetReports, FleetSummary, KindStats
from vyshkat.services.service_center import (
    InspectionResult,
    ServiceCenter,
    StandardServiceCenter,
)

__all__ = [
    "AssetRegistry",
    "FleetReports",
    "FleetSummary",
    "InspectionResult",
    "IntakeService",
    "KindStats",
    "NoviceAssessment",
    "NoviceRule",
    "ServiceCenter",
    "StandardServiceCenter",
]
