"""Custom exception types and FastAPI error-handler registration for TerraFlare."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class TerraFlareError(Exception):
    """Domain error with a machine-readable code and optional details dict."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    """Attach standard error handlers to a FastAPI application."""

    @app.exception_handler(TerraFlareError)
    async def _tf(_: Request, exc: TerraFlareError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = {
            "errors": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        }
        return JSONResponse(
            status_code=422,
            content=_body("invalid_parameters", "Invalid query parameters", details),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=_body("internal_error", str(exc)),
        )

