import asyncio
import io

from fastapi import UploadFile

from src.api.chat_materials import save_chat_uploads


def test_save_sanitizes_path_traversal(tmp_path) -> None:
    raw = io.BytesIO(b"x")
    uf = UploadFile(filename="../../../etc/passwd", file=raw)

    async def _run():
        return await save_chat_uploads(
            materials_root=tmp_path,
            domain_id="math",
            files=[uf],
        )

    saved = asyncio.run(_run())
    assert len(saved) == 1
    assert ".." not in saved[0].relative_posix
    assert "passwd" in saved[0].relative_posix
