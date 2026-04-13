"""从 ``Config`` 解析各领域 ``IndexVault``（Plan B 阶段 2）。"""

from __future__ import annotations

from pathlib import Path

from src.config import Config

from .index_vault import IndexVault


def resolve_index_vault_path(config: Config, domain_id: str) -> Path:
    """返回领域索引 Vault 根目录（已 expanduser/resolve）。

    优先使用 ``domain_index_paths[domain_id]``；若该领域未显式配置，则回退到
    ``<materials_vault_path 的父目录>/index_vaults/<domain_id>``。
    """
    raw = config.domain_index_paths.get(domain_id)
    if raw is not None:
        return Path(raw).expanduser().resolve()
    fallback_root = config.materials_vault_path.expanduser().resolve().parent / "index_vaults"
    return (fallback_root / domain_id).resolve()


def open_index_vault(config: Config, domain_id: str) -> IndexVault:
    """打开或初始化某领域的 ``IndexVault``（不存在则创建目录）。"""
    path = resolve_index_vault_path(config, domain_id)
    path.mkdir(parents=True, exist_ok=True)
    return IndexVault(path, domain_name=domain_id)
