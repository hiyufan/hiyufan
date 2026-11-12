"""拓展功能 4：超期工单预警。

定时任务每隔 ALERT_SCAN_INTERVAL_SECONDS 扫描一次：
    超时未派单：待派单状态，提交超过 48 小时
    超时未完工：待接单 / 维修中状态，派单超过 48 小时
已不满足条件的预警自动解除。设备科在看板上可"一键处理"：
    未派单 → 按故障类型 + 维修工负载自动派单
    未完工 → 向维修工发出催办（写入流转日志）
"""
import asyncio
import contextlib
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.enums import AlertType, OrderStatus
from app.core.exceptions import BizError, NotFound
from app.models import OrderAlert, RepairOrder, User
from app.schemas import AlertHandleOut, AlertOut, DispatchIn
from app.services import order_service, user_service
from app.services.ai import diagnosis

logger = logging.getLogger("cyf.jxrepair")

_RULES: dict[AlertType, tuple[frozenset[OrderStatus], str]] = {
    AlertType.DISPATCH_TIMEOUT: (frozenset({OrderStatus.PENDING}), "created_at"),
    AlertType.REPAIR_TIMEOUT: (frozenset({OrderStatus.ASSIGNED, OrderStatus.REPAIRING}), "dispatched_at"),
}


def scan(db: Session) -> dict[str, int]:
    """扫描一次，返回新增与自动解除的数量。可重复执行（幂等）。"""
    now = datetime.now()
    deadline = now - timedelta(hours=settings.alert_threshold_hours)
    open_alerts = {(a.order_id, a.alert_type): a
                   for a in db.scalars(select(OrderAlert).where(OrderAlert.is_handled.is_(False)))}
    # 人工处理过（如已催办）的预警，在一个阈值周期内不再重复提醒，否则催办后刷新页面又会冒出来
    recently_handled = set(db.execute(
        select(OrderAlert.order_id, OrderAlert.alert_type)
        .where(OrderAlert.handled_by.is_not(None), OrderAlert.handled_at >= deadline)
    ).all())
    created = resolved = 0
    still_overdue: set[tuple[int, AlertType]] = set()

    for alert_type, (statuses, time_field) in _RULES.items():
        column = getattr(RepairOrder, time_field)
        overdue = db.scalars(select(RepairOrder).where(RepairOrder.status.in_(statuses), column < deadline)).unique()
        for order in overdue:
            key = (order.id, alert_type)
            still_overdue.add(key)
            hours = int((now - getattr(order, time_field)).total_seconds() // 3600)
            if key in open_alerts:
                open_alerts[key].overdue_hours = hours
            elif key not in recently_handled:
                db.add(OrderAlert(order_id=order.id, alert_type=alert_type, overdue_hours=hours, created_at=now))
                created += 1

    for key, alert in open_alerts.items():
        if key not in still_overdue:  # 工单已被处理，预警自动解除
            alert.is_handled, alert.handled_at, alert.handle_note = True, now, "工单状态已变化，系统自动解除"
            resolved += 1
    db.commit()
    return {"created": created, "resolved": resolved}


def list_open(db: Session) -> list[AlertOut]:
    alerts = db.scalars(
        select(OrderAlert).where(OrderAlert.is_handled.is_(False)).order_by(OrderAlert.overdue_hours.desc())
    ).unique()
    return [
        AlertOut(id=a.id, order_id=a.order_id, order_no=a.order.order_no, device_name=a.order.device.device_name,
                 status_label=a.order.status.label, alert_type=a.alert_type.value, alert_label=a.alert_type.label,
                 overdue_hours=a.overdue_hours, created_at=a.created_at)
        for a in alerts
    ]


def handle(db: Session, operator: User, alert_id: int) -> AlertHandleOut:
    alert = db.get(OrderAlert, alert_id)
    if alert is None:
        raise NotFound("预警不存在")
    if alert.is_handled:
        raise BizError("该预警已处理")
    order = alert.order

    if alert.alert_type is AlertType.DISPATCH_TIMEOUT:
        category = diagnosis.top_category(db, order.fault_desc)
        candidates = user_service.recommend_repairers(db, category)
        if not candidates:
            raise BizError("当前没有在岗的维修工")
        best = candidates[0]
        order_service.dispatch(db, operator, order.id, DispatchIn(
            repairer_id=best.id, remark=f"超期自动派单：{'，'.join(best.reasons)}"))
        note = f"已自动派单给 {best.real_name}"
    else:
        order_service.urge(db, operator, order, alert.overdue_hours)
        note = f"已催办维修工 {order.repairer.real_name if order.repairer else ''}".strip()

    db.refresh(alert)
    if not alert.is_handled:  # dispatch() 内部可能已关闭该预警
        alert.is_handled, alert.handled_by, alert.handled_at = True, operator.id, datetime.now()
    alert.handle_note = note
    db.commit()
    return AlertHandleOut(alert_id=alert.id, handle_note=note)


def _scan_once() -> None:
    with SessionLocal() as db:
        result = scan(db)
        if result["created"] or result["resolved"]:
            logger.info("超期扫描完成：新增 %(created)s 条，自动解除 %(resolved)s 条", result)


async def run_scheduler(stop: asyncio.Event) -> None:
    """随应用启动的后台定时任务，应用关闭时通过 stop 事件优雅退出。"""
    while not stop.is_set():
        try:
            await asyncio.to_thread(_scan_once)  # 数据库操作是同步的，放到线程池中避免阻塞事件循环
        except Exception:  # 定时任务任何异常都不能让整个服务崩溃
            logger.exception("超期扫描失败")
        with contextlib.suppress(asyncio.TimeoutError):  # 超时 = 到了下一次扫描时间
            await asyncio.wait_for(stop.wait(), timeout=settings.alert_scan_interval_seconds)
