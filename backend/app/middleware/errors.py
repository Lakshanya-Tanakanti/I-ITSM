"""Translate exceptions into safe, consistent JSON error responses."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions import AppError

logger = logging.getLogger("iitsm.errors")


def _body(detail: str, code: str, **extra) -> dict:
    return {"detail": detail, "code": code, **extra}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(_body(exc.message, exc.code, **({"info": exc.details} if exc.details else {})),
                            status_code=exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            msg = err.get("msg", "Invalid value")
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
            errors.append({"field": ".".join(loc), "message": msg})
        summary = "; ".join(f"{e['field']}: {e['message']}" if e["field"] else e["message"] for e in errors[:4])
        return JSONResponse(_body(summary or "Invalid input.", "VALIDATION_ERROR", errors=errors), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(_body(str(exc.detail), "HTTP_ERROR"), status_code=exc.status_code,
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError):
        logger.warning("Integrity error: %s", exc)
        return JSONResponse(_body("The change conflicts with existing data.", "CONFLICT"), status_code=409)

    @app.exception_handler(SQLAlchemyError)
    async def db_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database failure")
        code = 503 if isinstance(exc, OperationalError) else 500
        return JSONResponse(_body("The database is temporarily unavailable. Please try again.", "DATABASE_ERROR"),
                            status_code=code)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error")  # stack trace goes to the log, never to the client
        return JSONResponse(_body("An unexpected error occurred.", "INTERNAL_ERROR"), status_code=500)
