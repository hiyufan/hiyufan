"""统计看板：全部在数据库中聚合，图表数据与库中实际数据一致。

设备科管理员看全厂数据，部门管理员只看本部门员工提交的工单。
"""
from datetime import date, datetime

from sqlalchemy import Select, func, select, text
from sqlalchemy.orm import Session

from app.core.enums import OrderStatus, UserRole
from app.models import Device, OrderAlert, RepairEvaluation, RepairOrder, User
from app.schemas import DurationOut, MonthlyOut, NameValue, RankingItem, SummaryOut


def _scoped(stmt: Select, user: User) -> Select:
    if user.role is UserRole.DEPT_ADMIN:
        return stmt.where(RepairOrder.reporter_id.in_(select(User.id).where(User.dept_id == user.dept_id)))
    return stmt


def _recent_months(n: int) -> list[str]:
    today = date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.append(f"{y:04d}-{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return months[::-1]


def summary(db: Session, user: User) -> SummaryOut:
    counts = dict(db.execute(_scoped(
        select(RepairOrder.status, func.count()).group_by(RepairOrder.status), user)).all())
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    archived_month = db.scalar(_scoped(select(func.count()).select_from(RepairOrder).where(
        RepairOrder.status == OrderStatus.ARCHIVED, RepairOrder.archived_at >= month_start), user)) or 0
    avg_score = db.scalar(_scoped(
        select(func.avg(RepairEvaluation.score)).join(RepairOrder, RepairOrder.id == RepairEvaluation.order_id), user))
    open_alerts = db.scalar(_scoped(
        select(func.count()).select_from(OrderAlert).join(RepairOrder, RepairOrder.id == OrderAlert.order_id)
        .where(OrderAlert.is_handled.is_(False)), user)) or 0
    return SummaryOut(
        total=sum(counts.values()),
        pending=counts.get(OrderStatus.PENDING, 0),
        in_progress=counts.get(OrderStatus.ASSIGNED, 0) + counts.get(OrderStatus.REPAIRING, 0),
        to_accept=counts.get(OrderStatus.TO_ACCEPT, 0),
        archived_this_month=archived_month,
        avg_score=round(float(avg_score), 2) if avg_score is not None else None,
        open_alerts=open_alerts,
    )


def monthly(db: Session, user: User, months: int = 6) -> MonthlyOut:
    labels = _recent_months(months)
    start = datetime.strptime(labels[0] + "-01", "%Y-%m-%d")

    def by_month(column) -> dict[str, int]:
        ym = func.date_format(column, "%Y-%m")
        stmt = _scoped(select(ym, func.count()).where(column >= start).group_by(ym), user)
        return dict(db.execute(stmt).all())

    submitted = by_month(RepairOrder.created_at)
    archived = by_month(RepairOrder.archived_at)
    return MonthlyOut(months=labels, submitted=[submitted.get(m, 0) for m in labels],
                      archived=[archived.get(m, 0) for m in labels])


def status_distribution(db: Session, user: User) -> list[NameValue]:
    rows = dict(db.execute(_scoped(select(RepairOrder.status, func.count()).group_by(RepairOrder.status), user)).all())
    return [NameValue(name=s.label, value=rows.get(s, 0)) for s in OrderStatus]


def _avg_hours(start, end):
    return func.avg(func.timestampdiff(text("MINUTE"), start, end)) / 60


def avg_duration(db: Session, user: User) -> DurationOut:
    stmt = _scoped(
        select(Device.category,
               _avg_hours(RepairOrder.created_at, RepairOrder.taken_at),
               _avg_hours(RepairOrder.taken_at, RepairOrder.completed_at))
        .join(Device, Device.id == RepairOrder.device_id)
        .where(RepairOrder.status == OrderStatus.ARCHIVED)
        .group_by(Device.category)
        .order_by(Device.category),
        user,
    )
    rows = db.execute(stmt).all()
    overall = db.scalar(_scoped(select(_avg_hours(RepairOrder.created_at, RepairOrder.archived_at))
                                .where(RepairOrder.status == OrderStatus.ARCHIVED), user))

    def r(v) -> float:
        return round(float(v or 0), 1)

    return DurationOut(categories=[c for c, *_ in rows], response_hours=[r(a) for _, a, _ in rows],
                       repair_hours=[r(b) for *_, b in rows], overall_hours=r(overall) if overall else None)


def device_ranking(db: Session, user: User, limit: int = 10) -> list[RankingItem]:
    cnt = func.count(RepairOrder.id).label("cnt")
    stmt = _scoped(
        select(Device.id, Device.device_code, Device.device_name, Device.category, cnt)
        .join(RepairOrder, RepairOrder.device_id == Device.id)
        .where(RepairOrder.status != OrderStatus.REJECTED)  # 被驳回的无效报修不计入故障次数
        .group_by(Device.id, Device.device_code, Device.device_name, Device.category)
        .order_by(cnt.desc(), Device.id)
        .limit(limit),
        user,
    )
    return [RankingItem(device_id=i, device_code=c, device_name=n, category=cat, count=k)
            for i, c, n, cat, k in db.execute(stmt).all()]
