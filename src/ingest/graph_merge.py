"""将 ``IngestionResult`` 合并进持久化的 graph_index 字典。"""

from __future__ import annotations

from typing import Any, Dict

from src.agent.base import IngestionResult


def merge_ingestion_into_graph(
    existing: Dict[str, Any],
    result: IngestionResult,
    material_rel_posix: str,
) -> Dict[str, Any]:
    """合并实体（按 id 覆盖）、追加关系，并记录每文件摄取元数据。"""
    raw_entities = existing.get("entities")
    if isinstance(raw_entities, dict):
        entities = dict(raw_entities)
    else:
        entities = {}
    for e in result.entities:
        entities[e.id] = e.to_dict()

    relations: list = list(existing.get("relations") or [])
    for r in result.relations:
        relations.append(r.to_dict())

    meta: Dict[str, Any] = dict(existing.get("ingest_meta") or {})
    meta[material_rel_posix] = {
        "entity_count": len(result.entities),
        "relation_count": len(result.relations),
        "success": result.success,
    }
    if result.error_message:
        meta[material_rel_posix]["error_message"] = result.error_message

    return {
        "entities": entities,
        "relations": relations,
        "ingest_meta": meta,
    }
