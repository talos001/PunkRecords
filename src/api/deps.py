from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from .auth import AuthStore, JWTService, UserRecord
from .errors import ApiError


@dataclass
class AuthContext:
    user: UserRecord
    access_payload: dict


def _extract_bearer(request: Request) -> str:
    raw = request.headers.get("Authorization", "").strip()
    if not raw.lower().startswith("bearer "):
        raise ApiError(401, "AUTH_REQUIRED", "请先登录")
    token = raw[7:].strip()
    if not token:
        raise ApiError(401, "AUTH_REQUIRED", "请先登录")
    return token


def require_auth(request: Request) -> AuthContext:
    token = _extract_bearer(request)
    jwt_svc: JWTService = request.app.state.jwt_service
    store: AuthStore = request.app.state.auth_store
    payload = jwt_svc.parse_access(token)
    user = store.get_user_by_id(str(payload.get("sub") or ""))
    if user is None:
        raise ApiError(401, "AUTH_INVALID_TOKEN", "登录态无效，请重新登录")
    if int(payload.get("ver") or -1) != user.token_version:
        raise ApiError(401, "AUTH_INVALID_TOKEN", "登录态无效，请重新登录")
    return AuthContext(user=user, access_payload=payload)


def require_ready_user(request: Request) -> AuthContext:
    ctx = require_auth(request)
    if not ctx.user.materials_path_confirmed:
        cfg = request.app.state.config
        effective = ctx.user.materials_path or str(cfg.materials_vault_path)
        raise ApiError(
            428,
            "MATERIALS_PATH_CONFIRM_REQUIRED",
            "请先确认材料库保存位置",
            extra={
                "effective_materials_path": effective,
            },
        )
    return ctx

