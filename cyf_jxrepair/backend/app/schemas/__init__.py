"""接口出入参模型。出参中的人名、设备名均通过外键关联查询得到，不在工单表冗余存储。"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import DeviceStatus, OrderAction, OrderStatus, Urgency, UserRole


class Option(BaseModel):
    value: str
    label: str


# ------------------------------------------------------------------ 用户 / 鉴权
class LoginIn(BaseModel):
    username: str = Field(min_length=2, max_length=30, examples=["emp01"])
    password: str = Field(min_length=6, max_length=64, examples=["123456"])


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    real_name: str
    phone: str | None
    role: UserRole
    role_label: str
    dept_id: int
    dept_name: str
    factory_area: str
    skills: list[str]
    is_active: bool
    created_at: datetime

    @classmethod
    def of(cls, u) -> "UserOut":
        return cls(
            id=u.id, username=u.username, real_name=u.real_name, phone=u.phone, role=u.role,
            role_label=u.role.label, dept_id=u.dept_id, dept_name=u.dept.dept_name,
            factory_area=u.dept.factory_area, skills=u.skill_list, is_active=u.is_active,
            created_at=u.created_at,
        )


class LoginOut(BaseModel):
    token: str
    expires_in: int = Field(description="有效期（秒）")
    user: UserOut


class PasswordChangeIn(BaseModel):
    old_password: str = Field(min_length=6, max_length=64)
    new_password: str = Field(min_length=6, max_length=64)


_PHONE_PATTERN = r"^1\d{10}$"


class UserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    real_name: str = Field(min_length=2, max_length=30)
    phone: str | None = Field(None, pattern=_PHONE_PATTERN)
    role: UserRole
    dept_id: int
    skills: list[str] = []
    password: str = Field("123456", min_length=6, max_length=64)


class UserUpdateIn(BaseModel):
    real_name: str | None = Field(None, min_length=2, max_length=30)
    phone: str | None = Field(None, pattern=_PHONE_PATTERN)
    role: UserRole | None = None
    dept_id: int | None = None
    skills: list[str] | None = None


class UserStatusIn(BaseModel):
    is_active: bool


class RepairerLoad(BaseModel):
    id: int
    real_name: str
    skills: list[str]
    active_orders: int = Field(description="手头未完成工单数")
    matched: bool = Field(False, description="擅长方向是否匹配本次故障")


class DeptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dept_name: str
    factory_area: str


# ------------------------------------------------------------------ 设备
class DeviceIn(BaseModel):
    device_code: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9-]+$")
    device_name: str = Field(min_length=2, max_length=50)
    category: str = Field(min_length=2, max_length=20)
    model: str | None = Field(None, max_length=50)
    dept_id: int
    location: str = Field(min_length=2, max_length=50)
    status: DeviceStatus = DeviceStatus.NORMAL
    purchase_date: date | None = None


class DeviceOut(BaseModel):
    id: int
    device_code: str
    device_name: str
    category: str
    model: str | None
    dept_id: int
    dept_name: str
    factory_area: str
    location: str
    status: DeviceStatus
    status_label: str
    purchase_date: date | None
    fault_count: int = 0

    @classmethod
    def of(cls, d, fault_count: int = 0) -> "DeviceOut":
        return cls(
            id=d.id, device_code=d.device_code, device_name=d.device_name, category=d.category,
            model=d.model, dept_id=d.dept_id, dept_name=d.dept.dept_name, factory_area=d.dept.factory_area,
            location=d.location, status=d.status, status_label=d.status.label,
            purchase_date=d.purchase_date, fault_count=fault_count,
        )


# ------------------------------------------------------------------ 工单
class UserBrief(BaseModel):
    id: int
    real_name: str
    phone: str | None = None


class DeviceBrief(BaseModel):
    id: int
    device_code: str
    device_name: str
    category: str
    location: str
    factory_area: str


class OrderBrief(BaseModel):
    id: int
    order_no: str
    device: DeviceBrief
    reporter: UserBrief
    repairer: UserBrief | None
    fault_desc: str
    urgency: Urgency
    urgency_label: str
    status: OrderStatus
    status_label: str
    reject_reason: str | None
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False


class LogOut(BaseModel):
    id: int
    action: OrderAction
    action_label: str
    from_status: str | None
    to_status: str
    content: str
    operator: UserBrief
    operator_role: str
    created_at: datetime


class EvaluationOut(BaseModel):
    score: int
    comment: str | None
    created_at: datetime


class OrderDetail(OrderBrief):
    photo_urls: list[str]
    repair_result: str | None
    dispatcher: UserBrief | None
    dispatched_at: datetime | None
    taken_at: datetime | None
    completed_at: datetime | None
    archived_at: datetime | None
    logs: list[LogOut]
    evaluation: EvaluationOut | None
    actions: list[Option] = Field(description="当前登录用户可执行的操作")


class DispatchIn(BaseModel):
    repairer_id: int
    remark: str | None = Field(None, max_length=200)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=2, max_length=200)

    @field_validator("reason")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("请至少填写 2 个字")
        return v


class CompleteIn(BaseModel):
    repair_result: str = Field(min_length=5, max_length=500)


class EvaluateIn(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(None, max_length=300)


class TakeIn(BaseModel):
    remark: str | None = Field(None, max_length=200)


# ------------------------------------------------------------------ 统计
class NameValue(BaseModel):
    name: str
    value: float


class SummaryOut(BaseModel):
    total: int
    pending: int
    in_progress: int
    to_accept: int
    archived_this_month: int
    avg_score: float | None
    open_alerts: int


class MonthlyOut(BaseModel):
    months: list[str]
    submitted: list[int]
    archived: list[int]


class DurationOut(BaseModel):
    categories: list[str]
    response_hours: list[float] = Field(description="提交 → 接单 平均小时")
    repair_hours: list[float] = Field(description="接单 → 完工 平均小时")
    overall_hours: float | None = Field(description="提交 → 归档 平均小时")


class RankingItem(BaseModel):
    device_id: int
    device_code: str
    device_name: str
    category: str
    count: int


# ------------------------------------------------------------------ AI 拓展
class DiagnoseIn(BaseModel):
    fault_desc: str = Field(min_length=4, max_length=500)
    device_id: int | None = None


class DiagnosisItem(BaseModel):
    category: str
    cause: str
    suggestion: str
    confidence: float = Field(description="0-1 置信度")
    matched_keywords: list[str]


class DiagnoseOut(BaseModel):
    engine: str = Field(description="local-kb：本地知识库；llm：大模型")
    items: list[DiagnosisItem]
    risk_level: str
    risk_tips: list[str]
    recommended_repairers: list[RepairerLoad]


class KnowledgeHit(BaseModel):
    order_id: int
    order_no: str
    device_name: str
    category: str
    fault_desc: str
    repair_result: str
    score: float
    archived_at: datetime | None


class SummaryCard(BaseModel):
    order_id: int
    order_no: str
    engine: str
    title: str
    fields: dict[str, str]
    text: str


class AlertOut(BaseModel):
    id: int
    order_id: int
    order_no: str
    device_name: str
    status_label: str
    alert_type: str
    alert_label: str
    overdue_hours: int
    created_at: datetime


class AlertHandleOut(BaseModel):
    alert_id: int
    handle_note: str
