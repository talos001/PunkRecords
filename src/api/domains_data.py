"""与 `frontend/src/domains.ts` 对齐的领域定义；服务端为权威来源之一。"""

from __future__ import annotations

from typing import Any, List, TypedDict


class DomainDict(TypedDict, total=False):
    id: str
    name: str
    description: str
    emoji: str
    variant: str
    enabled: bool


DOMAINS: List[DomainDict] = [
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


def domain_ids() -> List[str]:
    return [d["id"] for d in DOMAINS if d.get("enabled", True)]


def get_domain(domain_id: str) -> DomainDict | None:
    for d in DOMAINS:
        if d["id"] == domain_id and d.get("enabled", True):
            return d
    return None


def domains_response() -> dict[str, Any]:
    return {
        "domains": [dict(d) for d in DOMAINS if d.get("enabled", True)],
        "default_domain_id": DEFAULT_DOMAIN_ID,
    }
