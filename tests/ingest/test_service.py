"""摄取管线单测（Plan B 阶段 2）。"""

from pathlib import Path

import pytest

from src.config import Config
from src.ingest.service import ingest_material_file
from src.vaults.index_vault import IndexVault


def _minimal_config(materials: Path, index_root: Path, domain: str = "dom") -> Config:
    index_root.mkdir(parents=True, exist_ok=True)
    return Config(
        materials_vault_path=materials,
        domain_index_paths={domain: index_root},
        default_agent_backend="claude_code",
        llm_provider="fake",
        llm_model="claude-sonnet-4-20250514",
        llm_timeout_seconds=60.0,
    )


def test_ingest_writes_graph_and_wiki(tmp_path: Path) -> None:
    mat = tmp_path / "mat"
    idx = tmp_path / "idx"
    mat.mkdir()
    (mat / "note.md").write_text("# Hello\n\nbody", encoding="utf-8")
    cfg = _minimal_config(mat, idx)
    ingest_material_file(cfg, "dom", "note.md")

    iv = IndexVault(idx, "dom")
    g = iv.load_graph_index()
    assert "entities" in g
    assert "relations" in g
    assert "ingest_meta" in g
    assert "note.md" in g["ingest_meta"]

    w = iv.load_wiki_index()
    assert w.get("notes", {}).get("note.md", {}).get("title") == "Hello"


def test_ingest_requires_domain_mapping(tmp_path: Path) -> None:
    mat = tmp_path / "mat"
    mat.mkdir()
    (mat / "a.md").write_text("x")
    cfg = Config(
        materials_vault_path=mat,
        domain_index_paths={},
        default_agent_backend="claude_code",
        llm_provider="fake",
        llm_model="x",
        llm_timeout_seconds=60.0,
    )
    with pytest.raises(ValueError, match="domain_index_paths"):
        ingest_material_file(cfg, "missing", "a.md")


def test_ingest_rejects_escape(tmp_path: Path) -> None:
    mat = tmp_path / "mat"
    idx = tmp_path / "idx"
    mat.mkdir()
    cfg = _minimal_config(mat, idx)
    with pytest.raises(ValueError, match="材料路径"):
        ingest_material_file(cfg, "dom", "../outside.md")
