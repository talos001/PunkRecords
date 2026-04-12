from pathlib import Path

import pytest

from src.config import Config
from src.vaults.factory import open_index_vault, resolve_index_vault_path


def test_resolve_index_vault_path_missing(tmp_path: Path) -> None:
    cfg = Config(
        materials_vault_path=tmp_path / "m",
        domain_index_paths={},
        default_agent_backend="claude_code",
        llm_provider="fake",
        llm_model="x",
        llm_timeout_seconds=60.0,
    )
    with pytest.raises(ValueError, match="domain_index_paths"):
        resolve_index_vault_path(cfg, "x")


def test_open_index_vault_creates_state(tmp_path: Path) -> None:
    idx = tmp_path / "iv"
    cfg = Config(
        materials_vault_path=tmp_path / "m",
        domain_index_paths={"d": idx},
        default_agent_backend="claude_code",
        llm_provider="fake",
        llm_model="x",
        llm_timeout_seconds=60.0,
    )
    v = open_index_vault(cfg, "d")
    assert v.graph_index_path.exists()
    assert v.wiki_index_path.exists()
