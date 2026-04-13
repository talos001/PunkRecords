from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from .errors import ApiError


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


def _json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


@dataclass
class UserRecord:
    id: str
    username: str
    password_salt: str
    password_hash: str
    token_version: int
    materials_path: str | None
    materials_path_confirmed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "password_salt": self.password_salt,
            "password_hash": self.password_hash,
            "token_version": self.token_version,
            "materials_path": self.materials_path,
            "materials_path_confirmed": self.materials_path_confirmed,
        }


class AuthStore:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._lock = Lock()
        self._users: dict[str, UserRecord] = {}
        self._username_to_id: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self._file_path.is_file():
            return
        raw = json.loads(self._file_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return
        users = raw.get("users") or []
        if not isinstance(users, list):
            return
        for item in users:
            if not isinstance(item, dict):
                continue
            rec = UserRecord(
                id=str(item.get("id") or ""),
                username=str(item.get("username") or ""),
                password_salt=str(item.get("password_salt") or ""),
                password_hash=str(item.get("password_hash") or ""),
                token_version=int(item.get("token_version") or 0),
                materials_path=item.get("materials_path"),
                materials_path_confirmed=bool(item.get("materials_path_confirmed", False)),
            )
            if not rec.id or not rec.username:
                continue
            self._users[rec.id] = rec
            self._username_to_id[rec.username] = rec.id

    def _flush(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"users": [u.to_dict() for u in self._users.values()]}
        self._file_path.write_text(_json_dumps(data), encoding="utf-8")

    def create_user(self, username: str, password: str) -> UserRecord:
        with self._lock:
            if username in self._username_to_id:
                raise ApiError(409, "USER_EXISTS", "该用户名已存在")
            salt = secrets.token_hex(16)
            rec = UserRecord(
                id=secrets.token_hex(12),
                username=username,
                password_salt=salt,
                password_hash=_password_hash(password, salt),
                token_version=0,
                materials_path=None,
                materials_path_confirmed=False,
            )
            self._users[rec.id] = rec
            self._username_to_id[username] = rec.id
            self._flush()
            return rec

    def get_user_by_username(self, username: str) -> UserRecord | None:
        with self._lock:
            uid = self._username_to_id.get(username)
            if not uid:
                return None
            return self._users.get(uid)

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        with self._lock:
            return self._users.get(user_id)

    def update_materials_path(
        self, user_id: str, *, materials_path: str | None, confirmed: bool
    ) -> UserRecord:
        with self._lock:
            rec = self._users.get(user_id)
            if rec is None:
                raise ApiError(404, "USER_NOT_FOUND", "用户不存在")
            rec.materials_path = materials_path
            rec.materials_path_confirmed = confirmed
            self._flush()
            return rec

    def bump_token_version(self, user_id: str) -> None:
        with self._lock:
            rec = self._users.get(user_id)
            if rec is None:
                return
            rec.token_version += 1
            self._flush()


def _password_hash(password: str, salt: str) -> str:
    raw = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    )
    return raw.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    actual = _password_hash(password, salt)
    return hmac.compare_digest(actual, expected_hash)


class JWTService:
    def __init__(
        self,
        secret: str,
        issuer: str = "punkrecords",
        access_ttl_seconds: int = 15 * 60,
        refresh_ttl_seconds: int = 7 * 24 * 3600,
    ) -> None:
        self._secret = secret.encode("utf-8")
        self._issuer = issuer
        self._access_ttl = access_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds

    def _sign(self, header: dict[str, Any], payload: dict[str, Any]) -> str:
        h = _b64url_encode(_json_dumps(header).encode("utf-8"))
        p = _b64url_encode(_json_dumps(payload).encode("utf-8"))
        data = f"{h}.{p}".encode("ascii")
        sig = hmac.new(self._secret, data, hashlib.sha256).digest()
        return f"{h}.{p}.{_b64url_encode(sig)}"

    def _verify(self, token: str) -> dict[str, Any]:
        try:
            head, payload, sig = token.split(".")
            data = f"{head}.{payload}".encode("ascii")
            expected = hmac.new(self._secret, data, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _b64url_decode(sig)):
                raise ApiError(401, "AUTH_INVALID_TOKEN", "登录态无效，请重新登录")
            obj = json.loads(_b64url_decode(payload).decode("utf-8"))
            if not isinstance(obj, dict):
                raise ApiError(401, "AUTH_INVALID_TOKEN", "登录态无效，请重新登录")
            if obj.get("iss") != self._issuer:
                raise ApiError(401, "AUTH_INVALID_TOKEN", "登录态无效，请重新登录")
            exp = int(obj.get("exp") or 0)
            if exp <= int(time.time()):
                raise ApiError(401, "AUTH_TOKEN_EXPIRED", "登录已过期，请重新登录")
            return obj
        except ValueError as e:
            raise ApiError(401, "AUTH_INVALID_TOKEN", "登录态无效，请重新登录") from e
        except json.JSONDecodeError as e:
            raise ApiError(401, "AUTH_INVALID_TOKEN", "登录态无效，请重新登录") from e

    def issue_pair(self, user: UserRecord) -> tuple[str, str]:
        now = int(time.time())
        base = {
            "iss": self._issuer,
            "sub": user.id,
            "username": user.username,
            "ver": user.token_version,
            "iat": now,
        }
        access = dict(base)
        access["typ"] = "access"
        access["exp"] = now + self._access_ttl
        refresh = dict(base)
        refresh["typ"] = "refresh"
        refresh["exp"] = now + self._refresh_ttl
        return (
            self._sign({"alg": "HS256", "typ": "JWT"}, access),
            self._sign({"alg": "HS256", "typ": "JWT"}, refresh),
        )

    def parse_access(self, token: str) -> dict[str, Any]:
        payload = self._verify(token)
        if payload.get("typ") != "access":
            raise ApiError(401, "AUTH_INVALID_TOKEN", "登录态无效，请重新登录")
        return payload

    def parse_refresh(self, token: str) -> dict[str, Any]:
        payload = self._verify(token)
        if payload.get("typ") != "refresh":
            raise ApiError(401, "AUTH_INVALID_TOKEN", "登录态无效，请重新登录")
        return payload


def get_auth_secret() -> str:
    secret = os.environ.get("PUNKRECORDS_JWT_SECRET", "").strip()
    if secret:
        return secret
    # 本地开发默认密钥，生产环境应通过环境变量覆盖。
    return "punkrecords-dev-secret-change-me"

