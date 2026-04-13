from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


def _load_module(module_name: str, relative_path: str):
    root = Path(__file__).resolve().parents[2]
    file_path = root / relative_path
    spec = spec_from_file_location(module_name, file_path)
    assert spec is not None and spec.loader is not None
    mod = module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


_domain_store_mod = _load_module("punkrecords_domain_store", "src/api/domain_store.py")
_schemas_mod = _load_module("punkrecords_schemas", "src/api/schemas.py")
DomainStore = _domain_store_mod.DomainStore
DomainOut = _schemas_mod.DomainOut


def test_slug_generation_and_conflict_suffix_persisted(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)

    d1 = store.create_domain(name="Math Basics", description="A")
    d2 = store.create_domain(name="Math Basics", description="B")

    assert d1.id == "math-basics"
    assert d2.id == "math-basics-2"

    reloaded = DomainStore(db_path)
    ids = [d.id for d in reloaded.list_domains()]
    assert ids == ["math-basics", "math-basics-2"]


def test_archive_keeps_domain_readable(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)
    created = store.create_domain(name="Physics", description="C")

    archived = store.archive_domain(created.id)
    assert archived.is_archived is True
    assert archived.enabled is False
    assert archived.archived_at is not None

    active_ids = [d.id for d in store.list_domains()]
    assert created.id not in active_ids

    all_ids = [d.id for d in store.list_domains(include_archived=True)]
    assert created.id in all_ids

    fetched = store.get_domain(created.id)
    assert fetched is not None
    assert fetched.is_archived is True


def test_list_domains_include_archived_switches_view(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)
    active = store.create_domain(name="Active Domain", description="A")
    archived = store.create_domain(name="Archived Domain", description="B")
    store.archive_domain(archived.id)

    active_ids = [d.id for d in store.list_domains(include_archived=False)]
    archived_ids = [d.id for d in store.list_domains(include_archived=True)]

    assert active.id in active_ids
    assert archived.id not in active_ids
    assert archived.id in archived_ids
    assert active.id not in archived_ids


def test_archive_should_keep_first_archived_at(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)
    created = store.create_domain(name="Repeat Archive", description="R")
    first = store.archive_domain(created.id)
    second = store.archive_domain(created.id)

    assert first.archived_at is not None
    assert second.archived_at == first.archived_at


def test_domain_schema_supports_archive_contract() -> None:
    out = DomainOut(
        id="physics",
        name="Physics",
        description="desc",
        emoji="",
        variant="coral",
        enabled=False,
        is_archived=True,
        archived_at="2026-04-13T08:00:00Z",
    )
    data = out.model_dump()
    assert data["is_archived"] is True
    assert data["archived_at"] == "2026-04-13T08:00:00Z"
