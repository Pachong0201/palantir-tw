"""采集暂存：原样存档 + SHA256 指纹去重。先存后解析，重放成本为零。"""

import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import RawItem


def stage_raw(
    session: Session,
    source: str,
    payload: bytes,
    external_id: str | None = None,
    meta: dict | None = None,
) -> tuple[RawItem, bool]:
    """把一份原始抓取结果入库。返回 (raw_item, created)；已存在则返回旧记录。"""
    digest = hashlib.sha256(payload).hexdigest()
    existing = session.scalar(select(RawItem).where(RawItem.sha256 == digest))
    if existing is not None:
        return existing, False

    data_dir = Path(get_settings().data_dir) / "raw" / source
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{digest[:16]}"
    path.write_bytes(payload)

    item = RawItem(
        source=source,
        external_id=external_id,
        sha256=digest,
        content_path=str(path),
        meta=meta or {},
    )
    session.add(item)
    session.flush()
    return item, True
