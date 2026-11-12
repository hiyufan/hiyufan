"""拓展功能 2：维修知识库检索（同时是故障诊断"案例推理"的案例库）。

已归档工单的「故障描述 + 故障类别 + 处理结果」自动沉淀为知识库，用 BM25 检索相似案例。
故障描述在建索引时重复一次，相当于给"现象"字段加权（BM25F 的简化做法）：
用户检索时输入的是现象，现象相近比处理方法相近更重要。

索引缓存在内存中，归档工单数量或最新归档时间变化时自动重建，不需要手动维护。
"""
from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import OrderStatus
from app.models import RepairOrder
from app.schemas import KnowledgeHit
from app.services.ai.text import Bm25Index


@dataclass(frozen=True)
class Case:
    order_id: int
    order_no: str
    device_name: str
    device_category: str
    fault_category: str | None
    fault_desc: str
    repair_result: str
    archived_at: datetime | None


class _KnowledgeBase:
    def __init__(self) -> None:
        self._lock = Lock()
        self._version: tuple | None = None
        self._cases: list[Case] = []
        self._index: Bm25Index | None = None

    def _current_version(self, db: Session) -> tuple:
        return tuple(db.execute(
            select(func.count(), func.max(RepairOrder.archived_at))
            .where(RepairOrder.status == OrderStatus.ARCHIVED)
        ).one())

    def _ensure(self, db: Session) -> None:
        version = self._current_version(db)
        if version == self._version:
            return
        with self._lock:  # 双重检查，避免并发请求重复建索引
            if version == self._version:
                return
            orders = db.scalars(select(RepairOrder).where(
                RepairOrder.status == OrderStatus.ARCHIVED, RepairOrder.repair_result.is_not(None))).unique()
            self._cases = [
                Case(o.id, o.order_no, o.device.device_name, o.device.category, o.fault_category,
                     o.fault_desc, o.repair_result or "", o.archived_at)
                for o in orders
            ]
            self._index = Bm25Index([
                f"{c.fault_desc} {c.fault_desc} {c.fault_category or ''} {c.device_category} {c.repair_result}"
                for c in self._cases
            ])
            self._version = version

    def similar(self, db: Session, query: str, top_k: int = 8, min_match: float = 0.08,
                exclude_order_id: int | None = None) -> list[tuple[Case, float]]:
        """返回 [(案例, 匹配度)]。"""
        self._ensure(db)
        if not self._index or not query.strip():
            return []
        hits = [(self._cases[i], m) for i, m in self._index.search(query, top_k=top_k + 1, min_match=min_match)]
        return [(c, m) for c, m in hits if c.order_id != exclude_order_id][:top_k]

    def search(self, db: Session, query: str, top_k: int = 8, exclude_order_id: int | None = None) -> list[KnowledgeHit]:
        return [
            KnowledgeHit(order_id=c.order_id, order_no=c.order_no, device_name=c.device_name,
                         category=c.fault_category or c.device_category, fault_desc=c.fault_desc,
                         repair_result=c.repair_result, score=round(m, 3), archived_at=c.archived_at)
            for c, m in self.similar(db, query, top_k, exclude_order_id=exclude_order_id)
        ]

    def size(self, db: Session) -> int:
        self._ensure(db)
        return len(self._cases)


knowledge_base = _KnowledgeBase()
