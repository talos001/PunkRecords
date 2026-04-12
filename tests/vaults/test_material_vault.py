import tempfile
from pathlib import Path
from punkrecords.vaults.material_vault import MaterialVault


def test_iter_markdown_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "note1.md").write_text("# Note 1", encoding="utf-8")
        (tmp_path / "note2.md").write_text("# Note 2", encoding="utf-8")
        (tmp_path / "data").mkdir()
        (tmp_path / "data/note3.md").write_text("# Note 3", encoding="utf-8")
        (tmp_path / "image.png").write_bytes(b"fake")

        vault = MaterialVault(tmp_path)
        files = sorted(p.name for p in vault.iter_markdown_files())

        assert files == ["note1.md", "note2.md", "note3.md"]


def test_iter_ignores_hidden_directories():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "note1.md").write_text("# Note 1", encoding="utf-8")
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden/note2.md").write_text("# Hidden Note", encoding="utf-8")

        vault = MaterialVault(tmp_path)
        files = sorted(p.name for p in vault.iter_markdown_files())

        assert files == ["note1.md"]


def test_read_note_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        note = tmp_path / "test.md"
        note.write_text("# Test\n\nHello world", encoding="utf-8")

        vault = MaterialVault(tmp_path)
        content = vault.read_note(note.relative_to(tmp_path))

        assert content == "# Test\n\nHello world"


def test_get_relative_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vault = MaterialVault(tmp_path)

        absolute_path = tmp_path / "data" / "note.md"
        relative_path = vault.get_relative_path(absolute_path)

        assert relative_path == Path("data") / "note.md"
