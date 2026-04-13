from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import load_app_config
from src.llm.registry import LLMRegistry

from .auth import AuthStore, JWTService, get_auth_secret
from .domains_data import configure_domain_store
from .errors import ApiError
from .v1.router import router as v1_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = load_app_config()
    cfg_path_raw = os.environ.get("PUNKRECORDS_CONFIG")
    cfg_path = Path(cfg_path_raw).expanduser() if cfg_path_raw else None
    data_root = cfg_path.parent if cfg_path and cfg_path.is_file() else Path.cwd()
    configure_domain_store(data_root / "var" / "domains" / "domains.sqlite3")
    cfg.materials_vault_path.mkdir(parents=True, exist_ok=True)
    app.state.config = cfg
    app.state.llm_registry = LLMRegistry(cfg)
    app.state.auth_store = AuthStore((data_root / "var" / "auth" / "users.db"))
    app.state.jwt_service = JWTService(get_auth_secret())
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="PunkRecords API",
        description="班克记录 HTTP API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_exc_handler(request: Request, exc: HTTPException) -> JSONResponse:
        msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        body: dict[str, Any] = {
            "error": {
                "code": f"http_{exc.status_code}",
                "message": msg,
            }
        }
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(ApiError)
    async def api_err_handler(request: Request, exc: ApiError) -> JSONResponse:
        content: dict[str, Any] = {
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        }
        if exc.extra:
            content["error"]["details"] = exc.extra
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_exc_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": exc.errors().__repr__(),
                }
            },
        )

    app.include_router(v1_router, prefix=API_PREFIX)

    return app


app = create_app()
