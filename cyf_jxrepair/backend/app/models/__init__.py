"""ORM 模型：与 sql/01_schema.sql 一一对应。"""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import AlertType, DeviceStatus, OrderAction, OrderStatus, Urgency, UserRole


def _enum(enum_cls) -> Enum:
    """存储枚举的 value（英文编码），与建表脚本中的 ENUM 定义保持一致。"""
    return Enum(enum_cls, values_callable=lambda e: [m.value for m in e], native_enum=True, validate_strings=True)


class Dept(Base):
    __tablename__ = "sys_dept"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dept_name: Mapped[str] = mapped_column(String(50), unique=True)
    factory_area: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    real_name: Mapped[str] = mapped_column(String(30))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.EMPLOYEE)
    dept_id: Mapped[int] = mapped_column(ForeignKey("sys_dept.id"))
    skills: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    dept: Mapped[Dept] = relationship(lazy="joined")

    @property
    def skill_list(self) -> list[str]:
        return [s for s in (self.skills or "").split(",") if s]


class Device(Base):
    __tablename__ = "device"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_code: Mapped[str] = mapped_column(String(30), unique=True)
    device_name: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(20))
    model: Mapped[str | None] = mapped_column(String(50))
    dept_id: Mapped[int] = mapped_column(ForeignKey("sys_dept.id"))
    location: Mapped[str] = mapped_column(String(50))
    status: Mapped[DeviceStatus] = mapped_column(_enum(DeviceStatus), default=DeviceStatus.NORMAL)
    purchase_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    dept: Mapped[Dept] = relationship(lazy="joined")


class RepairOrder(Base):
    __tablename__ = "repair_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(14), unique=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("device.id"))
    reporter_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id"))
    dispatcher_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id"))
    repairer_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id"))
    fault_desc: Mapped[str] = mapped_column(String(500))
    photo_paths: Mapped[list[str] | None] = mapped_column(JSON)
    urgency: Mapped[Urgency] = mapped_column(_enum(Urgency), default=Urgency.NORMAL)
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus), default=OrderStatus.PENDING)
    reject_reason: Mapped[str | None] = mapped_column(String(200))
    repair_result: Mapped[str | None] = mapped_column(String(500))
    fault_category: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    device: Mapped[Device] = relationship(lazy="joined")
    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id], lazy="joined")
    dispatcher: Mapped[User | None] = relationship(foreign_keys=[dispatcher_id])
    repairer: Mapped[User | None] = relationship(foreign_keys=[repairer_id], lazy="joined")
    logs: Mapped[list["OrderLog"]] = relationship(
        back_populates="order", order_by="OrderLog.id", cascade="all, delete-orphan"
    )
    evaluation: Mapped["RepairEvaluation | None"] = relationship(back_populates="order", uselist=False)


class OrderLog(Base):
    __tablename__ = "order_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("repair_order.id", ondelete="CASCADE"))
    operator_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id"))
    action: Mapped[OrderAction] = mapped_column(_enum(OrderAction))
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    order: Mapped[RepairOrder] = relationship(back_populates="logs")
    operator: Mapped[User] = relationship(lazy="joined")


class RepairEvaluation(Base):
    __tablename__ = "repair_evaluation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("repair_order.id", ondelete="CASCADE"), unique=True)
    evaluator_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id"))
    score: Mapped[int] = mapped_column(SmallInteger)
    comment: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    order: Mapped[RepairOrder] = relationship(back_populates="evaluation")


class FaultKnowledge(Base):
    __tablename__ = "fault_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(20))
    keywords: Mapped[str] = mapped_column(String(200))
    cause: Mapped[str] = mapped_column(String(200))
    suggestion: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @property
    def keyword_list(self) -> list[str]:
        return [k.strip() for k in self.keywords.split(",") if k.strip()]


class OrderAlert(Base):
    __tablename__ = "order_alert"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("repair_order.id", ondelete="CASCADE"))
    alert_type: Mapped[AlertType] = mapped_column(_enum(AlertType))
    overdue_hours: Mapped[int] = mapped_column(Integer)
    is_handled: Mapped[bool] = mapped_column(Boolean, default=False)
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id"))
    handle_note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    handled_at: Mapped[datetime | None] = mapped_column(DateTime)

    order: Mapped[RepairOrder] = relationship(lazy="joined")


__all__ = [
    "Dept", "User", "Device", "RepairOrder", "OrderLog", "RepairEvaluation", "FaultKnowledge", "OrderAlert",
]
