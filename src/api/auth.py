from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
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
    llm_provider: str
    llm_model: str
    llm_base_url: str
    llm_api_key: str
    domain_material_paths: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "password_salt": self.password_salt,
            "password_hash": self.password_hash,
            "token_version": self.token_version,
            "materials_path": self.materials_path,
            "materials_path_confirmed": self.materials_path_confirmed,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "llm_api_key": "***" if self.llm_api_key else "",
            "domain_material_paths": self.domain_material_paths,
        }


class AuthStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = Lock()
        self._init_db()
        self._migrate_from_json_if_needed()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    token_version INTEGER NOT NULL DEFAULT 0,
                    materials_path TEXT,
                    materials_path_confirmed INTEGER NOT NULL DEFAULT 0,
                    llm_provider TEXT NOT NULL DEFAULT 'fake',
                    llm_model TEXT NOT NULL DEFAULT '',
                    llm_base_url TEXT NOT NULL DEFAULT '',
                    llm_api_key TEXT NOT NULL DEFAULT '',
                    domain_material_paths TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(users)").fetchall()
            }
            migrations = [
                (
                    "llm_provider",
                    "ALTER TABLE users ADD COLUMN llm_provider TEXT NOT NULL DEFAULT 'fake'",
                ),
                (
                    "llm_model",
                    "ALTER TABLE users ADD COLUMN llm_model TEXT NOT NULL DEFAULT ''",
                ),
                (
                    "llm_base_url",
                    "ALTER TABLE users ADD COLUMN llm_base_url TEXT NOT NULL DEFAULT ''",
                ),
                (
                    "llm_api_key",
                    "ALTER TABLE users ADD COLUMN llm_api_key TEXT NOT NULL DEFAULT ''",
                ),
                (
                    "domain_material_paths",
                    "ALTER TABLE users ADD COLUMN domain_material_paths TEXT NOT NULL DEFAULT '{}'",
                ),
            ]
            for col, stmt in migrations:
                if col not in cols:
                    conn.execute(stmt)
            conn.commit()

    def _from_row(self, row: sqlite3.Row | None) -> UserRecord | None:
        if row is None:
            return None
        raw_domain_paths = row["domain_material_paths"] if "domain_material_paths" in row.keys() else "{}"
        try:
            parsed = json.loads(raw_domain_paths or "{}")
            domain_paths = (
                {str(k): str(v) for k, v in parsed.items()} if isinstance(parsed, dict) else {}
            )
        except Exception:
            domain_paths = {}
        return UserRecord(
            id=str(row["id"]),
            username=str(row["username"]),
            password_salt=str(row["password_salt"]),
            password_hash=str(row["password_hash"]),
            token_version=int(row["token_version"]),
            materials_path=row["materials_path"],
            materials_path_confirmed=bool(row["materials_path_confirmed"]),
            llm_provider=str(row["llm_provider"] if "llm_provider" in row.keys() else "fake"),
            llm_model=str(row["llm_model"] if "llm_model" in row.keys() else ""),
            llm_base_url=str(row["llm_base_url"] if "llm_base_url" in row.keys() else ""),
            llm_api_key=str(row["llm_api_key"] if "llm_api_key" in row.keys() else ""),
            domain_material_paths=domain_paths,
        )

    def _migrate_from_json_if_needed(self) -> None:
        legacy_path = self._db_path.with_suffix(".json")
        if not legacy_path.is_file():
            return
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(1) AS cnt FROM users").fetchone()
            assert row is not None
            if int(row["cnt"]) > 0:
                return
        raw = json.loads(legacy_path.read_text(encoding="utf-8"))
        users = raw.get("users") if isinstance(raw, dict) else None
        if not isinstance(users, list):
            return
        with self._connect() as conn:
            for item in users:
                if not isinstance(item, dict):
                    continue
                uid = str(item.get("id") or "").strip()
                username = str(item.get("username") or "").strip()
                if not uid or not username:
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users (
                        id, username, password_salt, password_hash, token_version,
                        materials_path, materials_path_confirmed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        uid,
                        username,
                        str(item.get("password_salt") or ""),
                        str(item.get("password_hash") or ""),
                        int(item.get("token_version") or 0),
                        item.get("materials_path"),
                        1 if bool(item.get("materials_path_confirmed", False)) else 0,
                    ),
                )
            conn.commit()

    def create_user(self, username: str, password: str) -> UserRecord:
        with self._lock:
            with self._connect() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
            if exists is not None:
                raise ApiError(409, "USER_EXISTS", "该用户名已存在")
            salt, pwd_hash = build_password_record(password)
            rec = UserRecord(
                id=secrets.token_hex(12),
                username=username,
                password_salt=salt,
                password_hash=pwd_hash,
                token_version=0,
                materials_path=None,
                materials_path_confirmed=False,
                llm_provider="fake",
                llm_model="",
                llm_base_url="",
                llm_api_key="",
                domain_material_paths={},
            )
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO users (
                        id, username, password_salt, password_hash, token_version,
                        materials_path, materials_path_confirmed,
                        llm_provider, llm_model, llm_base_url, llm_api_key, domain_material_paths
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rec.id,
                        rec.username,
                        rec.password_salt,
                        rec.password_hash,
                        rec.token_version,
                        rec.materials_path,
                        1 if rec.materials_path_confirmed else 0,
                        rec.llm_provider,
                        rec.llm_model,
                        rec.llm_base_url,
                        rec.llm_api_key,
                        json.dumps(rec.domain_material_paths, ensure_ascii=False),
                    ),
                )
                conn.commit()
            return rec

    def reset_password(self, username: str, new_password: str) -> UserRecord:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
                rec = self._from_row(row)
                if rec is None:
                    raise ApiError(404, "USER_NOT_FOUND", "用户不存在")
                salt, pwd_hash = build_password_record(new_password)
                conn.execute(
                    """
                    UPDATE users
                    SET password_salt = ?, password_hash = ?, token_version = token_version + 1
                    WHERE id = ?
                    """,
                    (salt, pwd_hash, rec.id),
                )
                conn.commit()
                updated = conn.execute(
                    "SELECT * FROM users WHERE id = ?",
                    (rec.id,),
                ).fetchone()
            out = self._from_row(updated)
            assert out is not None
            return out

    def get_user_by_username(self, username: str) -> UserRecord | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
            return self._from_row(row)

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
            return self._from_row(row)

    def update_materials_path(
        self, user_id: str, *, materials_path: str | None, confirmed: bool
    ) -> UserRecord:
        with self._lock:
            with self._connect() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
                if exists is None:
                    raise ApiError(404, "USER_NOT_FOUND", "用户不存在")
                conn.execute(
                    """
                    UPDATE users
                    SET materials_path = ?, materials_path_confirmed = ?
                    WHERE id = ?
                    """,
                    (materials_path, 1 if confirmed else 0, user_id),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
            updated = self._from_row(row)
            assert updated is not None
            return updated

    def bump_token_version(self, user_id: str) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE users SET token_version = token_version + 1 WHERE id = ?",
                    (user_id,),
                )
                conn.commit()

    def update_user_settings(
        self,
        user_id: str,
        *,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
        materials_path: str | None = None,
        update_materials_path: bool = False,
        domain_material_paths: dict[str, str] | None = None,
    ) -> UserRecord:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
                rec = self._from_row(row)
                if rec is None:
                    raise ApiError(404, "USER_NOT_FOUND", "用户不存在")
                next_provider = llm_provider if llm_provider is not None else rec.llm_provider
                next_model = llm_model if llm_model is not None else rec.llm_model
                next_base_url = llm_base_url if llm_base_url is not None else rec.llm_base_url
                next_api_key = llm_api_key if llm_api_key is not None else rec.llm_api_key
                next_materials_path = materials_path if update_materials_path else rec.materials_path
                next_domain_paths = (
                    domain_material_paths
                    if domain_material_paths is not None
                    else rec.domain_material_paths
                )
                conn.execute(
                    """
                    UPDATE users
                    SET llm_provider = ?, llm_model = ?, llm_base_url = ?, llm_api_key = ?,
                        materials_path = ?, domain_material_paths = ?
                    WHERE id = ?
                    """,
                    (
                        next_provider,
                        next_model,
                        next_base_url,
                        next_api_key,
                        next_materials_path,
                        json.dumps(next_domain_paths, ensure_ascii=False),
                        user_id,
                    ),
                )
                conn.commit()
                updated = conn.execute(
                    "SELECT * FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
            out = self._from_row(updated)
            assert out is not None
            return out


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


def build_password_record(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    return salt, _password_hash(password, salt)


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

