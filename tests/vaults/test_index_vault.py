import tempfile
from pathlib import Path
from punkrecords.vaults.index_vault import IndexVault


def test_index_vault_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Don't manually create .punkrecords - IndexVault should do it
        vault = IndexVault(tmp_path, domain_name="test")
        assert vault.domain_name == "test"
        assert vault.graph_index_path.exists()
        assert vault.wiki_index_path.exists()


def test_create_material_reference():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vault = IndexVault(tmp_path, domain_name="test")

        # Test that we can store and retrieve material references
        ref = vault.create_material_reference(
            Path("raw/path/note.md"), "Note Title"
        )
        assert ref["title"] == "Note Title"
        assert ref["raw_path"] == "raw/path/note.md"


def test_graph_index_load_save():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vault = IndexVault(tmp_path, domain_name="test")

        # Test saving and loading graph index
        test_data = {"entities": {"test": {"id": "test", "name": "Test"}}}
        vault.save_graph_index(test_data)

        loaded = vault.load_graph_index()
        assert loaded == test_data


def test_wiki_index_load_save():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vault = IndexVault(tmp_path, domain_name="test")

        # Test saving and loading wiki index
        test_data = {"pages": {"Home": {"title": "Home", "links": []}}}
        vault.save_wiki_index(test_data)

        loaded = vault.load_wiki_index()
        assert loaded == test_data
