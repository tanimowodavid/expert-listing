class AppError(Exception):
    """Base class for every error the API knows how to report."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """The requested resource does not exist (maps to 404)."""


class ConflictError(AppError):
    """The request clashes with existing data, e.g. a duplicate email (maps to 409)."""


class InvalidReferenceError(AppError):
    """The request points at something that doesn't exist, e.g. an unknown agent_id (maps to 422)."""
