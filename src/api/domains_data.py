"""领域定义与动态 CRUD 数据存取。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Any, List, TypedDict


class DomainDict(TypedDict, total=False):
    id: str
    name: str
    description: str
    emoji: str
    variant: str
    enabled: bool


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
_LOCK = Lock()


def _domains_file_path() -> Path:
    return Path.cwd() / "var" / "domains" / "domains.json"


def _normalize_domain(domain: DomainDict) -> DomainDict:
    return {
        "id": str(domain.get("id") or "").strip(),
        "name": str(domain.get("name") or "").strip(),
        "description": str(domain.get("description") or ""),
        "emoji": str(domain.get("emoji") or ""),
        "variant": str(domain.get("variant") or "coral"),
        "enabled": bool(domain.get("enabled", True)),
    }


def _load_all_domains() -> list[DomainDict]:
    p = _domains_file_path()
    if not p.is_file():
        return [dict(d) for d in _INITIAL_DOMAINS]
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return [dict(d) for d in _INITIAL_DOMAINS]
    items = raw.get("domains")
    if not isinstance(items, list):
        return [dict(d) for d in _INITIAL_DOMAINS]
    out: list[DomainDict] = []
    for item in items:
        if isinstance(item, dict):
            norm = _normalize_domain(item)
            if norm["id"] and norm["name"]:
                out.append(norm)
    return out or [dict(d) for d in _INITIAL_DOMAINS]


def _save_all_domains(domains: list[DomainDict]) -> None:
    p = _domains_file_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"domains": domains}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return base or "domain"


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
    with _LOCK:
        domains = _load_all_domains()
        base = _slugify(clean_name)
        ids = {str(d.get("id") or "") for d in domains}
        idx = 1
        candidate = base
        while candidate in ids:
            idx += 1
            candidate = f"{base}-{idx}"
        domain: DomainDict = {
            "id": candidate,
            "name": clean_name,
            "description": description or "",
            "emoji": emoji or "",
            "variant": variant or "coral",
            "enabled": True,
        }
        domains.append(domain)
        _save_all_domains(domains)
        return dict(domain)


def update_domain(domain_id: str, updates: dict[str, Any]) -> DomainDict | None:
    with _LOCK:
        domains = _load_all_domains()
        for idx, item in enumerate(domains):
            if item.get("id") != domain_id:
                continue
            updated = dict(item)
            if "name" in updates and str(updates.get("name") or "").strip():
                updated["name"] = str(updates["name"]).strip()
            if "description" in updates:
                updated["description"] = str(updates.get("description") or "")
            if "emoji" in updates:
                updated["emoji"] = str(updates.get("emoji") or "")
            if "variant" in updates and str(updates.get("variant") or "").strip():
                updated["variant"] = str(updates["variant"]).strip()
            if "enabled" in updates:
                updated["enabled"] = bool(updates.get("enabled"))
            domains[idx] = _normalize_domain(updated)
            _save_all_domains(domains)
            return dict(domains[idx])
    return None


def delete_domain(domain_id: str) -> bool:
    with _LOCK:
        domains = _load_all_domains()
        next_domains = [d for d in domains if d.get("id") != domain_id]
        if len(next_domains) == len(domains):
            return False
        _save_all_domains(next_domains)
        return True


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
    return [d["id"] for d in _load_all_domains() if d.get("enabled", True)]


def get_domain(domain_id: str) -> DomainDict | None:
    for d in _load_all_domains():
        if d["id"] == domain_id and d.get("enabled", True):
            return d
    return None


def domains_response() -> dict[str, Any]:
    domains = [dict(d) for d in _load_all_domains() if d.get("enabled", True)]
    default_domain_id = DEFAULT_DOMAIN_ID
    if not any(d["id"] == default_domain_id for d in domains) and domains:
        default_domain_id = domains[0]["id"]
    return {
        "domains": domains,
        "default_domain_id": default_domain_id,
    }
