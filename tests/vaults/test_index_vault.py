import tempfile
from pathlib import Path
from punkrecords.vaults.index_vault import IndexVault


def test_index_vault_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / ".punkrecords").mkdir()

        vault = IndexVault(tmp_path, domain_name="test")
        assert vault.domain_name == "test"
        assert vault.graph_index_path.exists()
        assert vault.wiki_index_path.exists()


def test_reference_resolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / ".punkrecords").mkdir()
        vault = IndexVault(tmp_path, domain_name="test")

        # Test that we can store and retrieve material references
        ref = vault.create_material_reference(
            Path("raw/path/note.md"), "Note Title"
        )
        assert ref["title"] == "Note Title"
        assert ref["raw_path"] == "raw/path/note.md"
