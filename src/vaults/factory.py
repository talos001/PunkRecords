"""从 ``Config`` 解析各领域 ``IndexVault``（Plan B 阶段 2）。"""

from __future__ import annotations

from pathlib import Path

from src.config import Config

from .index_vault import IndexVault


def resolve_index_vault_path(config: Config, domain_id: str) -> Path:
    """返回领域索引 Vault 根目录（已 expanduser/resolve）；未配置则抛 ``ValueError``。"""
    raw = config.domain_index_paths.get(domain_id)
    if raw is None:
        raise ValueError(
            f"配置中缺少 domain_index_paths['{domain_id}']，无法写入该领域的索引 Vault"
        )
    return Path(raw).expanduser().resolve()


def open_index_vault(config: Config, domain_id: str) -> IndexVault:
    """打开或初始化某领域的 ``IndexVault``（不存在则创建目录）。"""
    path = resolve_index_vault_path(config, domain_id)
    path.mkdir(parents=True, exist_ok=True)
    return IndexVault(path, domain_name=domain_id)
