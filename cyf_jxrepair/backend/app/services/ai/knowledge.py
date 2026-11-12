"""拓展功能 2：维修知识库检索。

已归档工单的「故障描述 + 处理结果」自动沉淀为知识库，用 TF-IDF 余弦相似度检索相似案例。
索引在内存中缓存，有新工单归档时（数量或最新归档时间变化）自动重建。
"""
from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import OrderStatus
from app.models import RepairOrder
from app.schemas import KnowledgeHit
from app.services.ai.text import TfidfIndex


@dataclass
class _Doc:
    order_id: int
    order_no: str
    device_name: str
    category: str
    fault_desc: str
    repair_result: str
    archived_at: datetime | None


class _KnowledgeBase:
    def __init__(self) -> None:
        self._lock = Lock()
        self._version: tuple | None = None
        self._docs: list[_Doc] = []
        self._index: TfidfIndex | None = None

    def _current_version(self, db: Session) -> tuple:
        return tuple(db.execute(
            select(func.count(), func.max(RepairOrder.archived_at))
            .where(RepairOrder.status == OrderStatus.ARCHIVED)
        ).one())

    def _ensure(self, db: Session) -> None:
        version = self._current_version(db)
        if version == self._version:
            return
        with self._lock:
            if version == self._version:
                return
            orders = db.scalars(select(RepairOrder).where(
                RepairOrder.status == OrderStatus.ARCHIVED, RepairOrder.repair_result.is_not(None))).unique()
            self._docs = [
                _Doc(o.id, o.order_no, o.device.device_name, o.device.category, o.fault_desc,
                     o.repair_result or "", o.archived_at)
                for o in orders
            ]
            # 故障描述权重更高（重复一次），处理结果作为补充
            self._index = TfidfIndex([f"{d.fault_desc} {d.fault_desc} {d.category} {d.repair_result}"
                                      for d in self._docs])
            self._version = version

    def search(self, db: Session, query: str, top_k: int = 8, exclude_order_id: int | None = None) -> list[KnowledgeHit]:
        self._ensure(db)
        if not self._index or not query.strip():
            return []
        hits = []
        for idx, score in self._index.search(query, top_k=top_k + 1):
            doc = self._docs[idx]
            if doc.order_id == exclude_order_id:
                continue
            hits.append(KnowledgeHit(
                order_id=doc.order_id, order_no=doc.order_no, device_name=doc.device_name,
                category=doc.category, fault_desc=doc.fault_desc, repair_result=doc.repair_result,
                score=round(score, 3), archived_at=doc.archived_at,
            ))
        return hits[:top_k]

    def size(self, db: Session) -> int:
        self._ensure(db)
        return len(self._docs)


knowledge_base = _KnowledgeBase()
