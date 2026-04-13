from pathlib import Path

from src.api.domain_store import DomainStore
from src.api.schemas import DomainOut


def test_slug_generation_and_conflict_suffix_persisted(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)

    d1 = store.create_domain(name="Math Basics", description="A")
    d2 = store.create_domain(name="Math Basics", description="B")

    assert d1.id == "math-basics"
    assert d2.id == "math-basics-2"

    reloaded = DomainStore(db_path)
    ids = [d.id for d in reloaded.list_domains(include_archived=True)]
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
