from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppError,
    ConflictError,
    InvalidReferenceError,
    NotFoundError,
)

STATUS_BY_ERROR: dict[type[AppError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    InvalidReferenceError: 422,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        for error_type, status_code in STATUS_BY_ERROR.items():
            if isinstance(exc, error_type):
                return JSONResponse(status_code=status_code, content={"detail": exc.message})
        # An AppError nobody mapped is our bug. Don't leak its message.
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})