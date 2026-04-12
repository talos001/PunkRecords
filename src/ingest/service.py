"""单文件摄取：材料 Vault → Agent → 领域 IndexVault。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

# 确保各 Agent 在 get_agent_registry 中完成注册
import src.agent.claude_code  # noqa: F401
import src.agent.codex  # noqa: F401
import src.agent.opencode  # noqa: F401

from src.agent.base import BaseAgent, IngestionResult
from src.agent.registry import get_agent_registry
from src.config import Config
from src.vaults.factory import open_index_vault
from src.vaults.material_vault import MaterialVault

from .graph_merge import merge_ingestion_into_graph
from .wiki_merge import merge_note_wiki_entry


def _resolve_material_file(config: Config, relative_path: str) -> Path:
    """``relative_path`` 相对于材料 Vault 根；必须落在根内且为文件。"""
    root = config.materials_vault_path.expanduser().resolve()
    rel = Path(relative_path)
    if rel.is_absolute():
        raise ValueError("path 必须为相对材料 Vault 的路径")
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise ValueError("材料路径必须位于 materials_vault_path 之下") from e
    if not candidate.is_file():
        raise ValueError(f"文件不存在或不是普通文件: {candidate}")
    return candidate


def _note_title_from_path(material_abs: Path) -> str:
    try:
        text = material_abs.read_text(encoding="utf-8")
    except OSError:
        return material_abs.stem
    m = re.match(r"^\s*#\s+(.+)$", text.splitlines()[0] if text else "", re.MULTILINE)
    if m:
        return m.group(1).strip()
    return material_abs.stem


def build_agent_instance(config: Config, backend_name: str) -> BaseAgent:
    reg = get_agent_registry()
    cls = reg.get_agent(backend_name)
    if cls is None:
        raise ValueError(f"未注册的 agent 后端: {backend_name}")
    key = config.llm_api_key or config.agent_api_key
    return cls(api_key=key)


def ingest_material_file(
    config: Config,
    domain_id: str,
    relative_path: str,
    *,
    agent_backend: Optional[str] = None,
) -> IngestionResult:
    """
    摄取单个材料文件，写入对应领域的 graph_index / wiki_index。

    ``relative_path`` 使用 POSIX 风格相对路径（如 ``math/incoming/.../x.md``）。
    """
    material_abs = _resolve_material_file(config, relative_path)
    root = config.materials_vault_path.expanduser().resolve()
    rel_posix = material_abs.relative_to(root).as_posix()

    backend = (agent_backend or config.default_agent_backend or "claude_code").strip()
    agent = build_agent_instance(config, backend)
    result = agent.ingest(material_abs)

    index_vault = open_index_vault(config, domain_id)
    graph = index_vault.load_graph_index()
    merged = merge_ingestion_into_graph(graph, result, rel_posix)
    index_vault.save_graph_index(merged)

    wiki = index_vault.load_wiki_index()
    title = _note_title_from_path(material_abs)
    index_vault.save_wiki_index(
        merge_note_wiki_entry(wiki, rel_posix, title),
    )

    return result


def material_vault_for_config(config: Config) -> MaterialVault:
    """材料 Vault 封装（只读遍历等）。"""
    return MaterialVault(config.materials_vault_path.expanduser().resolve())
