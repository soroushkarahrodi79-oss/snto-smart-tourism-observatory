"""Typed CRUD repositories, one per Fase 5 resource (step 5.2)."""
from __future__ import annotations

from src.persistence.repositories.alert import AlertRepository
from src.persistence.repositories.audit_log import AuditLogRepository
from src.persistence.repositories.base import Repository
from src.persistence.repositories.decision import DecisionRepository
from src.persistence.repositories.field_verification import (
    FieldVerificationRepository,
)
from src.persistence.repositories.intervention import InterventionRepository
from src.persistence.repositories.managed_asset import ManagedAssetRepository
from src.persistence.repositories.observation import ObservationRepository
from src.persistence.repositories.organization import OrganizationRepository
from src.persistence.repositories.recommendation import RecommendationRepository
from src.persistence.repositories.territory import TerritoryRepository
from src.persistence.repositories.user import UserRepository

__all__ = [
    "Repository",
    "AlertRepository",
    "AuditLogRepository",
    "DecisionRepository",
    "FieldVerificationRepository",
    "InterventionRepository",
    "ManagedAssetRepository",
    "ObservationRepository",
    "OrganizationRepository",
    "RecommendationRepository",
    "TerritoryRepository",
    "UserRepository",
]
