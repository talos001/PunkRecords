"""轻量 wiki_index 更新（阶段 2：按材料路径登记标题）。"""

from __future__ import annotations

from typing import Any, Dict


def merge_note_wiki_entry(
    existing: Dict[str, Any],
    material_rel_posix: str,
    title: str,
) -> Dict[str, Any]:
    notes: Dict[str, Any] = dict(existing.get("notes") or {})
    notes[material_rel_posix] = {"title": title}
    return {"notes": notes}
