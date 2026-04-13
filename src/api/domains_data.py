"""领域定义与动态 CRUD 数据存取。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, TypedDict

from .domain_store import DomainRecord, DomainStore

class DomainDict(TypedDict, total=False):
    id: str
    name: str
    description: str
    emoji: str
    variant: str
    enabled: bool
    is_archived: bool
    archived_at: str | None


_INITIAL_DOMAINS: List[DomainDict] = [
    {
        "id": "early-childhood",
        "name": "幼儿发展",
        "description": "育儿、早教与儿童发展相关",
        "emoji": "🌱",
        "variant": "coral",
        "enabled": True,
    },
    {
        "id": "math",
        "name": "数学",
        "description": "数学概念、习题与拓展",
        "emoji": "🔢",
        "variant": "indigo",
        "enabled": True,
    },
    {
        "id": "english",
        "name": "英语",
        "description": "英语学习与阅读材料",
        "emoji": "✨",
        "variant": "mint",
        "enabled": True,
    },
    {
        "id": "chinese",
        "name": "语文",
        "description": "阅读、写作与语言文字积累",
        "emoji": "📖",
        "variant": "amber",
        "enabled": True,
    },
    {
        "id": "history",
        "name": "历史",
        "description": "历史事件、人物与脉络梳理",
        "emoji": "🏛️",
        "variant": "rose",
        "enabled": True,
    },
]

DEFAULT_DOMAIN_ID = "early-childhood"
_STORE_PATH = Path(__file__).resolve().parents[2] / "var" / "domains" / "domains.sqlite3"
_STORE = DomainStore(_STORE_PATH)
_BOOTSTRAPPED = False


def _record_to_domain(rec: DomainRecord) -> DomainDict:
    return {
        "id": rec.id,
        "name": rec.name,
        "description": rec.description,
        "emoji": rec.emoji,
        "variant": rec.variant,
        "enabled": rec.enabled and (not rec.is_archived),
        "is_archived": rec.is_archived,
        "archived_at": rec.archived_at,
    }


def configure_domain_store(store_path: Path) -> None:
    global _STORE, _STORE_PATH, _BOOTSTRAPPED
    _STORE_PATH = store_path
    _STORE = DomainStore(_STORE_PATH)
    _BOOTSTRAPPED = False


def _ensure_bootstrapped() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    for item in _INITIAL_DOMAINS:
        _STORE.seed_domain(
            domain_id=item["id"],
            name=item["name"],
            description=item.get("description", ""),
            emoji=item.get("emoji", ""),
            variant=item.get("variant", "coral"),
            enabled=bool(item.get("enabled", True)),
        )
    _BOOTSTRAPPED = True


def _list_active_domains() -> list[DomainDict]:
    _ensure_bootstrapped()
    out: list[DomainDict] = []
    for rec in _STORE.list_domains(view="active"):
        out.append(_record_to_domain(rec))
    return out


def create_domain(
    *,
    name: str,
    description: str = "",
    emoji: str = "",
    variant: str = "coral",
) -> DomainDict:
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("name is required")
    _ensure_bootstrapped()
    rec = _STORE.create_domain(
        name=clean_name,
        description=description or "",
        emoji=emoji or "",
        variant=variant or "coral",
    )
    return _record_to_domain(rec)


def update_domain(domain_id: str, updates: dict[str, Any]) -> DomainDict | None:
    _ensure_bootstrapped()
    current = _STORE.get_domain(domain_id)
    if current is None:
        return None
    raw_name = updates.get("name") if "name" in updates else None
    if raw_name is not None and not str(raw_name).strip():
        raise ValueError("name is required")
    raw_variant = updates.get("variant") if "variant" in updates else None
    if raw_variant is not None and not str(raw_variant).strip():
        raise ValueError("variant is required")
    rec = _STORE.update_domain(
        domain_id,
        name=(str(raw_name).strip() if raw_name is not None else None),
        description=(str(updates.get("description") or "") if "description" in updates else None),
        emoji=(str(updates.get("emoji") or "") if "emoji" in updates else None),
        variant=(str(raw_variant).strip() if raw_variant is not None else None),
        enabled=(bool(updates.get("enabled")) if "enabled" in updates else None),
    )
    return _record_to_domain(rec)


def delete_domain(domain_id: str) -> bool:
    _ensure_bootstrapped()
    return _STORE.delete_domain(domain_id)


def archive_domain(domain_id: str) -> DomainDict | None:
    _ensure_bootstrapped()
    try:
        rec = _STORE.archive_domain(domain_id)
    except KeyError:
        return None
    return _record_to_domain(rec)


def active_domain_count() -> int:
    _ensure_bootstrapped()
    return len(_STORE.list_domains(view="active"))


def has_materials_data(materials_root: Path, domain_id: str) -> bool:
    dom_dir = materials_root / domain_id
    if not dom_dir.exists():
        return False
    for p in dom_dir.rglob("*"):
        if p.is_file():
            return True
    return False


def has_index_data(index_root: Path) -> bool:
    if not index_root.exists():
        return False
    for p in index_root.rglob("*"):
        if not p.is_file():
            continue
        name = p.name
        if name in {"graph_index.json", "wiki_index.json"}:
            raw = p.read_text(encoding="utf-8").strip()
            if raw in {"", "{}", "{ }"}:
                continue
        return True
    return False


def domain_ids() -> List[str]:
    return [d["id"] for d in _list_active_domains()]


def get_domain(domain_id: str) -> DomainDict | None:
    _ensure_bootstrapped()
    rec = _STORE.get_domain(domain_id)
    if rec is None:
        return None
    out = _record_to_domain(rec)
    if not out.get("enabled", True):
        return None
    return out


def domain_exists(domain_id: str) -> bool:
    _ensure_bootstrapped()
    return _STORE.get_domain(domain_id) is not None


def domains_response() -> dict[str, Any]:
    domains = _list_active_domains()
    default_domain_id = DEFAULT_DOMAIN_ID
    if not any(d["id"] == default_domain_id for d in domains) and domains:
        default_domain_id = domains[0]["id"]
    return {
        "domains": domains,
        "default_domain_id": default_domain_id,
    }
