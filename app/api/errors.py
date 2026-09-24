import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    AppError,
    ConflictError,
    InvalidReferenceError,
    NotFoundError,
)

logger = logging.getLogger(__name__)

# Domain error -> (HTTP status, machine-readable code). The only place they meet.
DOMAIN_ERRORS: dict[type[AppError], tuple[int, str]] = {
    NotFoundError: (404, "not_found"),
    ConflictError: (409, "conflict"),
    InvalidReferenceError: (422, "invalid_reference"),
}

CODE_BY_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "too_many_requests",
    503: "service_unavailable",
}

# PostgreSQL SQLSTATE codes for constraint failures
CHECK_VIOLATION = "23514"
NOT_NULL_VIOLATION = "23502"


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    details: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    for error_type, (status_code, code) in DOMAIN_ERRORS.items():
        if isinstance(exc, error_type):
            return error_response(status_code, code, exc.message)
    # An AppError nobody mapped is our bug. Don't leak its message.
    return error_response(500, "internal_error", "Internal server error")


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Deliberately keep only "where" and "what". FastAPI's default body also echoes
    # the raw input (which may contain personal data) and internal context objects.
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"].removeprefix("Value error, "),
        }
        for error in exc.errors()
    ]
    return error_response(
        422, "validation_error", "Request validation failed", details=details
    )


async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    # Covers HTTPException raised by our code AND Starlette's own 404 (unknown route)
    # and 405 (wrong method), which never reach our routes.
    code = CODE_BY_STATUS.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return error_response(exc.status_code, code, message, headers=exc.headers)


async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    # Safety net. Services check business rules first, but the database is the final
    # authority, and two simultaneous requests can both pass a pre-check.
    sqlstate = getattr(exc.orig, "sqlstate", None)
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    logger.warning("Integrity error: sqlstate=%s constraint=%s", sqlstate, constraint)

    if sqlstate in {CHECK_VIOLATION, NOT_NULL_VIOLATION}:
        return error_response(422, "invalid_data", "The data violates a database rule")
    return error_response(409, "conflict", "The request conflicts with existing data")


async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Database error", exc_info=exc)
    if isinstance(exc, OperationalError):
        return error_response(503, "service_unavailable", "Database unavailable")
    return error_response(500, "internal_error", "Internal server error")


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(500, "internal_error", "Internal server error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(IntegrityError, handle_integrity_error)
    app.add_exception_handler(SQLAlchemyError, handle_database_error)
    app.add_exception_handler(Exception, handle_unexpected_error)