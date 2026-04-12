from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import yaml


@dataclass
class Config:
    materials_vault_path: Path
    domain_index_paths: Dict[str, Path]
    default_agent_backend: str
    agent_api_key: Optional[str] = None
    llm_provider: str = "fake"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_timeout_seconds: float = 120.0


def load_config(config_path: Path) -> Config:
    """Load configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Config(
        materials_vault_path=Path(data["materials_vault_path"]).expanduser(),
        domain_index_paths={
            k: Path(v).expanduser()
            for k, v in (data.get("domain_index_paths") or {}).items()
        },
        default_agent_backend=data.get("default_agent_backend", "claude_code"),
        agent_api_key=data.get("agent_api_key"),
        llm_provider=str(data.get("llm_provider", "anthropic")),
        llm_model=str(data.get("llm_model", "claude-sonnet-4-20250514")),
        llm_timeout_seconds=float(data.get("llm_timeout_seconds", 120.0)),
    )


def default_config() -> Config:
    """无 YAML 时的默认配置（单机开发 / 测试）；材料目录默认 ./var/materials_vault。"""
    raw = os.environ.get("PUNKRECORDS_MATERIALS_VAULT", "./var/materials_vault")
    return Config(
        materials_vault_path=Path(raw).expanduser().resolve(),
        domain_index_paths={},
        default_agent_backend="claude_code",
        agent_api_key=os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY"),
        llm_provider=os.environ.get("PUNKRECORDS_LLM_PROVIDER", "fake"),
        llm_model=os.environ.get(
            "PUNKRECORDS_LLM_MODEL", "claude-sonnet-4-20250514"
        ),
        llm_timeout_seconds=float(os.environ.get("PUNKRECORDS_LLM_TIMEOUT", "120")),
    )


def load_app_config() -> Config:
    """供 HTTP 服务使用：优先 ``PUNKRECORDS_CONFIG`` 指向的 YAML，否则 ``default_config``。"""
    path_raw = os.environ.get("PUNKRECORDS_CONFIG")
    if path_raw:
        p = Path(path_raw).expanduser()
        if p.is_file():
            return load_config(p)
    return default_config()
