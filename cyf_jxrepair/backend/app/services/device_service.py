"""设备台账管理。"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import PageParams
from app.core.enums import DeviceStatus
from app.core.exceptions import Conflict, NotFound
from app.core.response import PageResult, page_of
from app.models import Dept, Device, RepairOrder
from app.schemas import DeviceIn, DeviceOut


def _get(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise NotFound("设备不存在")
    return device


def _fault_counts(db: Session, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    rows = db.execute(
        select(RepairOrder.device_id, func.count())
        .where(RepairOrder.device_id.in_(ids))
        .group_by(RepairOrder.device_id)
    ).all()
    return dict(rows)


def list_devices(
    db: Session, page: PageParams, keyword: str | None, category: str | None,
    status: DeviceStatus | None, dept_id: int | None,
) -> PageResult[DeviceOut]:
    stmt = select(Device)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(Device.device_code.like(like), Device.device_name.like(like),
                              Device.location.like(like), Device.model.like(like)))
    if category:
        stmt = stmt.where(Device.category == category)
    if status:
        stmt = stmt.where(Device.status == status)
    if dept_id:
        stmt = stmt.where(Device.dept_id == dept_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Device.dept_id, Device.device_code).offset(page.offset).limit(page.size)).all()
    counts = _fault_counts(db, [d.id for d in rows])
    return page_of([DeviceOut.of(d, counts.get(d.id, 0)) for d in rows], total, page.page, page.size)


def device_options(db: Session) -> list[DeviceOut]:
    """报修下拉框：只列出未报废的设备。"""
    rows = db.scalars(
        select(Device).where(Device.status != DeviceStatus.SCRAPPED).order_by(Device.dept_id, Device.device_code)
    ).all()
    return [DeviceOut.of(d) for d in rows]


def categories(db: Session) -> list[str]:
    return list(db.scalars(select(Device.category).distinct().order_by(Device.category)))


def _check_unique(db: Session, code: str, exclude_id: int | None = None) -> None:
    stmt = select(Device.id).where(Device.device_code == code)
    if exclude_id:
        stmt = stmt.where(Device.id != exclude_id)
    if db.scalar(stmt):
        raise Conflict(f"设备编号 {code} 已存在")


def create_device(db: Session, data: DeviceIn) -> DeviceOut:
    if db.get(Dept, data.dept_id) is None:
        raise NotFound("使用部门不存在")
    _check_unique(db, data.device_code)
    device = Device(**data.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return DeviceOut.of(device)


def update_device(db: Session, device_id: int, data: DeviceIn) -> DeviceOut:
    device = _get(db, device_id)
    _check_unique(db, data.device_code, exclude_id=device_id)
    for key, value in data.model_dump().items():
        setattr(device, key, value)
    db.commit()
    db.refresh(device)
    return DeviceOut.of(device, _fault_counts(db, [device.id]).get(device.id, 0))


def delete_device(db: Session, device_id: int) -> None:
    device = _get(db, device_id)
    used = db.scalar(select(func.count()).where(RepairOrder.device_id == device_id))
    if used:
        raise Conflict(f"该设备已有 {used} 条报修记录，不能删除，可将状态改为「已报废」")
    db.delete(device)
    db.commit()
