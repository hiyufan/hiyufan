"""报修工单业务：提交、查询、状态流转。

数据范围（行级权限）：
    普通员工     只能看自己提交的工单
    部门管理员   能看本部门员工提交的工单
    维修工       只能看指派给自己的工单
    设备科管理员 能看全部工单
"""
from collections.abc import Callable
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import PageParams
from app.core.enums import (
    ACTIVE_STATUSES,
    AlertType,
    DeviceStatus,
    OrderAction,
    OrderStatus,
    Urgency,
    UserRole,
)
from app.core.exceptions import BizError, Conflict, Forbidden, NotFound
from app.core.response import PageResult, page_of
from app.models import Device, OrderAlert, OrderLog, RepairEvaluation, RepairOrder, User
from app.schemas import (
    CompleteIn,
    DeviceBrief,
    DispatchIn,
    EvaluateIn,
    EvaluationOut,
    LogOut,
    Option,
    OrderBrief,
    OrderDetail,
    UserBrief,
)
from app.services import file_service
from app.services.workflow import available_actions, ensure_can

REPORTER_ROLES = (UserRole.EMPLOYEE, UserRole.DEPT_ADMIN)


# ------------------------------------------------------------------ 数据范围
def scope_filter(stmt: Select, user: User) -> Select:
    match user.role:
        case UserRole.EMPLOYEE:
            return stmt.where(RepairOrder.reporter_id == user.id)
        case UserRole.DEPT_ADMIN:
            dept_users = select(User.id).where(User.dept_id == user.dept_id)
            return stmt.where(RepairOrder.reporter_id.in_(dept_users))
        case UserRole.REPAIRER:
            return stmt.where(RepairOrder.repairer_id == user.id)
        case _:
            return stmt


def get_scoped(db: Session, user: User, order_id: int, *, for_update: bool = False) -> RepairOrder:
    stmt = scope_filter(select(RepairOrder).where(RepairOrder.id == order_id), user)
    if for_update:
        stmt = stmt.with_for_update(of=RepairOrder)  # 行锁：防止两个管理员同时派单
    order = db.scalar(stmt)
    if order is None:
        # 越权访问与不存在返回同样的提示，不暴露其他人工单是否存在
        raise NotFound("工单不存在或无权查看")
    return order


# ------------------------------------------------------------------ 序列化
def _user_brief(u: User | None) -> UserBrief | None:
    return UserBrief(id=u.id, real_name=u.real_name, phone=u.phone) if u else None


def _device_brief(d: Device) -> DeviceBrief:
    return DeviceBrief(id=d.id, device_code=d.device_code, device_name=d.device_name,
                       category=d.category, location=d.location, factory_area=d.dept.factory_area)


def _open_alert_ids(db: Session, order_ids: list[int]) -> set[int]:
    if not order_ids:
        return set()
    return set(db.scalars(select(OrderAlert.order_id).where(
        OrderAlert.order_id.in_(order_ids), OrderAlert.is_handled.is_(False))))


def to_brief(o: RepairOrder, overdue: bool = False) -> OrderBrief:
    return OrderBrief(
        id=o.id, order_no=o.order_no, device=_device_brief(o.device), reporter=_user_brief(o.reporter),
        repairer=_user_brief(o.repairer), fault_desc=o.fault_desc, urgency=o.urgency,
        urgency_label=o.urgency.label, status=o.status, status_label=o.status.label,
        reject_reason=o.reject_reason, created_at=o.created_at, updated_at=o.updated_at, is_overdue=overdue,
    )


def to_detail(db: Session, o: RepairOrder, user: User) -> OrderDetail:
    brief = to_brief(o, bool(_open_alert_ids(db, [o.id])))
    logs = [
        LogOut(id=lg.id, action=lg.action, action_label=lg.action.label, from_status=lg.from_status,
               to_status=lg.to_status, content=lg.content, operator=_user_brief(lg.operator),
               operator_role=lg.operator.role.label, created_at=lg.created_at)
        for lg in o.logs
    ]
    ev = o.evaluation
    return OrderDetail(
        **brief.model_dump(),
        photo_urls=file_service.to_urls(o.photo_paths),
        repair_result=o.repair_result, dispatcher=_user_brief(o.dispatcher),
        dispatched_at=o.dispatched_at, taken_at=o.taken_at, completed_at=o.completed_at,
        archived_at=o.archived_at, logs=logs,
        evaluation=EvaluationOut(score=ev.score, comment=ev.comment, created_at=ev.created_at) if ev else None,
        actions=[Option(value=a.value, label=a.label) for a in available_actions(o, user)],
    )


# ------------------------------------------------------------------ 查询
def list_orders(
    db: Session, user: User, page: PageParams, *,
    statuses: list[OrderStatus] | None = None, keyword: str | None = None,
    urgency: Urgency | None = None, device_id: int | None = None,
) -> PageResult[OrderBrief]:
    stmt = scope_filter(select(RepairOrder), user)
    if statuses:
        stmt = stmt.where(RepairOrder.status.in_(statuses))
    if urgency:
        stmt = stmt.where(RepairOrder.urgency == urgency)
    if device_id:
        stmt = stmt.where(RepairOrder.device_id == device_id)
    if keyword and keyword.strip():
        like = f"%{keyword.strip()}%"  # ORM 参数化绑定，不拼接 SQL 字符串
        stmt = stmt.where(or_(
            RepairOrder.order_no.like(like),
            RepairOrder.fault_desc.like(like),
            RepairOrder.device_id.in_(select(Device.id).where(
                or_(Device.device_name.like(like), Device.device_code.like(like)))),
            RepairOrder.reporter_id.in_(select(User.id).where(User.real_name.like(like))),
        ))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(RepairOrder.created_at.desc(), RepairOrder.id.desc()).offset(page.offset).limit(page.size)
    ).unique().all()
    overdue = _open_alert_ids(db, [o.id for o in rows])
    return page_of([to_brief(o, o.id in overdue) for o in rows], total, page.page, page.size)


def status_counts(db: Session, user: User) -> dict[str, int]:
    """当前用户可见范围内各状态的数量，用于列表页的状态标签角标。"""
    stmt = scope_filter(select(RepairOrder.status, func.count()).group_by(RepairOrder.status), user)
    counts = {s.value: 0 for s in OrderStatus}
    counts.update({s.value: n for s, n in db.execute(stmt).all()})
    return counts


# ------------------------------------------------------------------ 提交 / 重新提交
def _next_order_no(db: Session, now: datetime) -> str:
    prefix = f"{settings.order_prefix}{now:%Y%m%d}"
    last = db.scalar(
        select(RepairOrder.order_no).where(RepairOrder.order_no.like(f"{prefix}%"))
        .order_by(RepairOrder.order_no.desc()).limit(1).with_for_update()
    )
    seq = int(last[-3:]) + 1 if last else 1
    if seq > 999:
        raise BizError("今日工单数量已达上限")
    return f"{prefix}{seq:03d}"


def _check_device(db: Session, device_id: int, exclude_order_id: int | None = None) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise NotFound("报修设备不存在")
    if device.status is DeviceStatus.SCRAPPED:
        raise BizError("该设备已报废，不能报修")
    stmt = select(RepairOrder.order_no).where(
        RepairOrder.device_id == device_id,
        RepairOrder.status.in_(ACTIVE_STATUSES | {OrderStatus.PENDING}),
    )
    if exclude_order_id:
        stmt = stmt.where(RepairOrder.id != exclude_order_id)
    if dup := db.scalar(stmt.limit(1)):
        raise Conflict(f"该设备已有处理中的报修单 {dup}，请勿重复提交")
    return device


def _add_log(db: Session, order: RepairOrder, operator: User, action: OrderAction,
             from_status: OrderStatus | None, content: str) -> None:
    db.add(OrderLog(order_id=order.id, operator_id=operator.id, action=action,
                    from_status=from_status.value if from_status else None,
                    to_status=order.status.value, content=content, created_at=datetime.now()))


def create_order(db: Session, user: User, device_id: int, fault_desc: str,
                 urgency: Urgency, photos: list[UploadFile]) -> RepairOrder:
    if user.role not in REPORTER_ROLES:
        raise Forbidden("仅普通员工和部门管理员可以提交报修")
    _check_device(db, device_id)
    paths = file_service.save_images(photos)  # 先校验并落盘，失败时不会产生脏数据

    try:
        for attempt in range(3):  # 极端并发下编号冲突时重试
            now = datetime.now()
            order = RepairOrder(
                order_no=_next_order_no(db, now), device_id=device_id, reporter_id=user.id,
                fault_desc=fault_desc.strip(), urgency=urgency, photo_paths=paths or None,
                status=OrderStatus.PENDING, created_at=now,
            )
            db.add(order)
            try:
                db.flush()
                break
            except IntegrityError:
                db.rollback()
                if attempt == 2:
                    raise
        _add_log(db, order, user, OrderAction.SUBMIT, None, f"提交报修：{order.fault_desc}")
        db.commit()
    except Exception:
        db.rollback()
        file_service.remove_files(paths)
        raise
    return order


def resubmit(db: Session, user: User, order_id: int, device_id: int, fault_desc: str,
             urgency: Urgency, photos: list[UploadFile], keep_photos: bool) -> RepairOrder:
    order = get_scoped(db, user, order_id, for_update=True)
    rule = ensure_can(order, OrderAction.RESUBMIT, user)
    _check_device(db, device_id, exclude_order_id=order.id)

    new_paths = file_service.save_images(photos)
    old_paths = list(order.photo_paths or [])
    if keep_photos:
        merged = old_paths + new_paths
        if len(merged) > settings.upload_max_count:
            file_service.remove_files(new_paths)
            raise BizError(f"照片总数不能超过 {settings.upload_max_count} 张")
        removed = []
    else:
        merged, removed = new_paths, old_paths

    from_status = order.status
    order.device_id = device_id
    order.fault_desc = fault_desc.strip()
    order.urgency = urgency
    order.photo_paths = merged or None
    order.status = rule.target
    order.dispatcher_id = None
    _add_log(db, order, user, OrderAction.RESUBMIT, from_status, f"修改后重新提交：{order.fault_desc}")
    try:
        db.commit()
    except Exception:
        db.rollback()
        file_service.remove_files(new_paths)
        raise
    file_service.remove_files(removed)
    return order


# ------------------------------------------------------------------ 状态流转
def _transit(db: Session, user: User, order_id: int, action: OrderAction,
             apply: Callable[[RepairOrder, datetime], str]) -> RepairOrder:
    """通用流转模板：加锁取单 → 状态机校验 → 执行业务修改 → 改状态 → 写日志 → 提交。"""
    order = get_scoped(db, user, order_id, for_update=True)
    rule = ensure_can(order, action, user)
    from_status = order.status
    now = datetime.now()
    content = apply(order, now)
    order.status = rule.target
    _add_log(db, order, user, action, from_status, content)
    db.commit()
    return order


def dispatch(db: Session, user: User, order_id: int, data: DispatchIn) -> RepairOrder:
    repairer = db.get(User, data.repairer_id)
    if repairer is None or repairer.role is not UserRole.REPAIRER or not repairer.is_active:
        raise BizError("请选择一名在岗的维修工")

    def apply(order: RepairOrder, now: datetime) -> str:
        order.repairer_id = repairer.id
        order.dispatcher_id = user.id
        order.dispatched_at = now
        order.reject_reason = None
        return f"派单给维修工 {repairer.real_name}" + (f"；备注：{data.remark}" if data.remark else "")

    order = _transit(db, user, order_id, OrderAction.DISPATCH, apply)
    _close_alerts(db, order.id, AlertType.DISPATCH_TIMEOUT, user, "已派单")
    return order


def reject(db: Session, user: User, order_id: int, reason: str) -> RepairOrder:
    def apply(order: RepairOrder, _: datetime) -> str:
        order.reject_reason = reason
        order.dispatcher_id = user.id
        return f"驳回：{reason}"

    order = _transit(db, user, order_id, OrderAction.REJECT, apply)
    _close_alerts(db, order.id, AlertType.DISPATCH_TIMEOUT, user, "已驳回")
    return order


def take(db: Session, user: User, order_id: int, remark: str | None) -> RepairOrder:
    def apply(order: RepairOrder, now: datetime) -> str:
        order.taken_at = now
        order.device.status = DeviceStatus.REPAIRING  # 设备状态联动
        return "维修工已接单" + (f"：{remark}" if remark else "，前往现场处理")

    return _transit(db, user, order_id, OrderAction.TAKE, apply)


def complete(db: Session, user: User, order_id: int, data: CompleteIn) -> RepairOrder:
    def apply(order: RepairOrder, now: datetime) -> str:
        order.repair_result = data.repair_result.strip()
        order.completed_at = now
        return f"完工提交：{order.repair_result}"

    order = _transit(db, user, order_id, OrderAction.COMPLETE, apply)
    _close_alerts(db, order.id, AlertType.REPAIR_TIMEOUT, user, "已完工")
    return order


def evaluate(db: Session, user: User, order_id: int, data: EvaluateIn) -> RepairOrder:
    """验收通过 + 评价 + 归档，三件事在同一个事务里完成。"""
    def apply(order: RepairOrder, now: datetime) -> str:
        if order.evaluation is not None:
            raise Conflict("该工单已评价")
        db.add(RepairEvaluation(order_id=order.id, evaluator_id=user.id, score=data.score,
                                comment=(data.comment or "").strip() or None, created_at=now))
        order.archived_at = now
        _release_device(db, order)
        return f"验收通过，评分 {data.score} 星" + (f"：{data.comment}" if data.comment else "")

    order = _transit(db, user, order_id, OrderAction.ACCEPT, apply)
    _add_log(db, order, user, OrderAction.ARCHIVE, OrderStatus.ARCHIVED, "工单已归档")
    db.commit()
    return order


def accept_fail(db: Session, user: User, order_id: int, reason: str) -> RepairOrder:
    def apply(order: RepairOrder, _: datetime) -> str:
        order.completed_at = None
        return f"验收不通过：{reason}"

    return _transit(db, user, order_id, OrderAction.ACCEPT_FAIL, apply)


def _release_device(db: Session, order: RepairOrder) -> None:
    """工单归档后，如果该设备没有其他处理中的工单，恢复为正常状态。"""
    others = db.scalar(select(func.count()).where(
        RepairOrder.device_id == order.device_id, RepairOrder.id != order.id,
        RepairOrder.status.in_(ACTIVE_STATUSES)))
    if not others and order.device.status is DeviceStatus.REPAIRING:
        order.device.status = DeviceStatus.NORMAL


def _close_alerts(db: Session, order_id: int, alert_type: AlertType, user: User, note: str) -> None:
    alerts = db.scalars(select(OrderAlert).where(
        OrderAlert.order_id == order_id, OrderAlert.alert_type == alert_type, OrderAlert.is_handled.is_(False)))
    now = datetime.now()
    for alert in alerts:
        alert.is_handled, alert.handled_by, alert.handled_at, alert.handle_note = True, user.id, now, note
    db.commit()


def urge(db: Session, operator: User, order: RepairOrder, hours: int) -> None:
    """超期催办：只记日志，不改变状态。"""
    db.add(OrderLog(order_id=order.id, operator_id=operator.id, action=OrderAction.URGE,
                    from_status=order.status.value, to_status=order.status.value,
                    content=f"工单已超时 {hours} 小时未完工，设备科催办", created_at=datetime.now()))
