from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import yaml

_log = logging.getLogger(__name__)


def _optional_nonempty_str(value: object | None) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


@dataclass
class Config:
    materials_vault_path: Path
    domain_index_paths: Dict[str, Path]
    default_agent_backend: str
    agent_api_key: Optional[str] = None  # 历史字段；LLM 优先用 llm_api_key
    llm_provider: str = "fake"
    llm_base_url: Optional[str] = None  # Anthropic 兼容 API 根 URL；默认官方
    llm_api_key: Optional[str] = None  # 未设时回退 agent_api_key
    llm_model: str = "claude-sonnet-4-20250514"
    llm_timeout_seconds: float = 120.0
    chat_auto_ingest: bool = False
    """``POST /chat`` 在附件落盘后是否自动对新材料执行摄取（需配置 ``domain_index_paths``）。"""


def _llm_provider_from_yaml(data: dict) -> str:
    """支持 ``llm_provider`` 或简写 ``provider``；缺省为 fake（与 Config 默认值一致）。"""
    raw = data.get("llm_provider") or data.get("provider")
    if raw is None or str(raw).strip() == "":
        return "fake"
    return str(raw).strip().lower()


def load_config(config_path: Path) -> Config:
    """Load configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        data = {}

    llm_key = data.get("llm_api_key") or data.get("agent_api_key")
    return Config(
        materials_vault_path=Path(data["materials_vault_path"]).expanduser(),
        domain_index_paths={
            k: Path(v).expanduser()
            for k, v in (data.get("domain_index_paths") or {}).items()
        },
        default_agent_backend=data.get("default_agent_backend", "claude_code"),
        agent_api_key=_optional_nonempty_str(data.get("agent_api_key")),
        llm_provider=_llm_provider_from_yaml(data),
        llm_base_url=_optional_nonempty_str(data.get("llm_base_url")),
        llm_api_key=_optional_nonempty_str(llm_key),
        llm_model=str(data.get("llm_model", "claude-sonnet-4-20250514")),
        llm_timeout_seconds=float(data.get("llm_timeout_seconds", 120.0)),
        chat_auto_ingest=bool(data.get("chat_auto_ingest", False)),
    )


def default_config() -> Config:
    """无 YAML 时的默认配置（单机开发 / 测试）；材料目录默认 ./var/materials_vault。"""
    raw = os.environ.get("PUNKRECORDS_MATERIALS_VAULT", "./var/materials_vault")
    base_url = (
        os.environ.get("PUNKRECORDS_LLM_BASE_URL")
        or os.environ.get("ANTHROPIC_BASE_URL")
    )
    base_url = base_url.strip() if base_url else None
    llm_key = (
        os.environ.get("PUNKRECORDS_LLM_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    legacy_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
        "OPENAI_API_KEY"
    )
    return Config(
        materials_vault_path=Path(raw).expanduser().resolve(),
        domain_index_paths={},
        default_agent_backend="claude_code",
        agent_api_key=legacy_key,
        llm_provider=os.environ.get("PUNKRECORDS_LLM_PROVIDER", "fake"),
        llm_base_url=base_url,
        llm_api_key=llm_key,
        llm_model=os.environ.get(
            "PUNKRECORDS_LLM_MODEL", "claude-sonnet-4-20250514"
        ),
        llm_timeout_seconds=float(os.environ.get("PUNKRECORDS_LLM_TIMEOUT", "120")),
        chat_auto_ingest=os.environ.get("PUNKRECORDS_CHAT_AUTO_INGEST", "").lower()
        in ("1", "true", "yes"),
    )


def load_app_config() -> Config:
    """供 HTTP 服务使用：优先 ``PUNKRECORDS_CONFIG`` 指向的 YAML，否则尝试当前工作目录下的 ``config.yaml``，最后 ``default_config``。"""
    path_raw = os.environ.get("PUNKRECORDS_CONFIG")
    if path_raw:
        p = Path(path_raw).expanduser()
        if p.is_file():
            cfg = load_config(p)
            _log.info(
                "已加载配置 llm_provider=%s（来源 PUNKRECORDS_CONFIG=%s）",
                cfg.llm_provider,
                p,
            )
            return cfg
    cwd_cfg = Path.cwd() / "config.yaml"
    if cwd_cfg.is_file():
        cfg = load_config(cwd_cfg)
        _log.info(
            "已加载配置 llm_provider=%s（来源 当前目录 config.yaml=%s）",
            cfg.llm_provider,
            cwd_cfg.resolve(),
        )
        return cfg
    cfg = default_config()
    _log.info(
        "已加载配置 llm_provider=%s（来源 环境变量 default_config，未使用 YAML 文件）",
        cfg.llm_provider,
    )
    return cfg
