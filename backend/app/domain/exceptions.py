"""Custom exception hierarchy.

Every exception carries an HTTP status code and a stable machine readable
`code`, so the API layer can translate domain failures into safe responses
without leaking internals.
"""


class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTHENTICATION_FAILED"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "PERMISSION_DENIED"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class IncidentNotFoundError(NotFoundError):
    code = "INCIDENT_NOT_FOUND"


class ServiceNotFoundError(NotFoundError):
    code = "SERVICE_NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class DuplicateResourceError(ConflictError):
    code = "DUPLICATE_RESOURCE"


class InvalidTransitionError(ConflictError):
    code = "INVALID_STATE_TRANSITION"


class TechnicianUnavailableError(ConflictError):
    code = "TECHNICIAN_UNAVAILABLE"


class WorkloadExceededError(ConflictError):
    code = "TECHNICIAN_WORKLOAD_EXCEEDED"


class MissingSkillError(ConflictError):
    code = "TECHNICIAN_MISSING_SKILL"


class InvalidInputError(AppError):
    status_code = 422
    code = "INVALID_INPUT"


class MissingSlaConfigurationError(AppError):
    status_code = 422
    code = "MISSING_SLA_CONFIGURATION"


class DatabaseUnavailableError(AppError):
    status_code = 503
    code = "DATABASE_ERROR"
