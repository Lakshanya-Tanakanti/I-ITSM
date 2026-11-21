"""Importing this package registers every entity on `Base.metadata`."""
from app.models.config_entities import IncidentCategory, Service, SlaPolicy, SystemSetting
from app.models.user import SupportTeam, TechnicianProfile, TechnicianSkill, User
from app.models.incident import (
    EmployeeFeedback, Incident, InvestigationNote, Resolution, SlaViolation,
)
from app.models.notification import Notification
from app.models.audit import AuditLog

__all__ = [
    "AuditLog", "EmployeeFeedback", "Incident", "IncidentCategory", "InvestigationNote",
    "Notification", "Resolution", "Service", "SlaPolicy", "SlaViolation", "SupportTeam",
    "SystemSetting", "TechnicianProfile", "TechnicianSkill", "User",
]
