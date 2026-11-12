from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.core.deps import CurrentUser, DbSession, Pagination, require_roles
from app.core.enums import OrderStatus, Urgency, UserRole
from app.core.response import ApiResponse, PageResult, ok
from app.models import User
from app.schemas import (
    CompleteIn,
    DispatchIn,
    EvaluateIn,
    OrderBrief,
    OrderDetail,
    ReasonIn,
    SummaryCard,
    TakeIn,
)
from app.services import order_service
from app.services.ai import summary

router = APIRouter(prefix="/api/orders", tags=["报修工单"])

DeviceAdmin = Annotated[User, Depends(require_roles(UserRole.DEVICE_ADMIN))]
Repairer = Annotated[User, Depends(require_roles(UserRole.REPAIRER))]
Reporter = Annotated[User, Depends(require_roles(UserRole.EMPLOYEE, UserRole.DEPT_ADMIN))]

FaultDesc = Annotated[str, Form(min_length=5, max_length=500, description="故障描述，至少 5 个字")]
Photos = Annotated[list[UploadFile], File(description="现场照片，jpg/png，单张 ≤ 5MB，最多 3 张")]


def _detail(db: DbSession, order, user: User) -> OrderDetail:
    db.refresh(order)  # 重新加载流转日志、评价等关联数据
    return order_service.to_detail(db, order, user)


@router.post("", summary="提交报修（multipart，含图片上传）", response_model=ApiResponse[OrderDetail])
def create_order(
    db: DbSession, user: Reporter,
    device_id: Annotated[int, Form(description="报修设备 ID")],
    fault_desc: FaultDesc,
    urgency: Annotated[Urgency, Form()] = Urgency.NORMAL,
    photos: Photos = [],  # noqa: B006  FastAPI 声明式默认值，不会被修改
):
    order = order_service.create_order(db, user, device_id, fault_desc, urgency, photos)
    return ok(_detail(db, order, user), f"报修已提交，工单号 {order.order_no}")


@router.get("", summary="工单列表（分页 + 状态筛选 + 关键词检索，按角色限定数据范围）",
            response_model=ApiResponse[PageResult[OrderBrief]])
def list_orders(
    db: DbSession, user: CurrentUser, page: Pagination,
    status: Annotated[list[OrderStatus] | None, Query(description="可传多个：?status=PENDING&status=REJECTED")] = None,
    keyword: Annotated[str | None, Query(max_length=50, description="工单号/故障描述/设备/报修人")] = None,
    urgency: Urgency | None = None,
    device_id: int | None = None,
):
    return ok(order_service.list_orders(db, user, page, statuses=status, keyword=keyword,
                                        urgency=urgency, device_id=device_id))


@router.get("/status-counts", summary="各状态工单数量（列表页角标）", response_model=ApiResponse[dict[str, int]])
def status_counts(db: DbSession, user: CurrentUser):
    return ok(order_service.status_counts(db, user))


@router.get("/{order_id}", summary="工单详情（含流转日志、评价、可执行操作）", response_model=ApiResponse[OrderDetail])
def get_order(order_id: int, db: DbSession, user: CurrentUser):
    return ok(order_service.to_detail(db, order_service.get_scoped(db, user, order_id), user))


@router.get("/{order_id}/summary", summary="工单智能摘要", response_model=ApiResponse[SummaryCard])
def order_summary(order_id: int, db: DbSession, user: CurrentUser):
    return ok(summary.build(db, order_service.get_scoped(db, user, order_id), use_llm=True))


@router.post("/{order_id}/dispatch", summary="派单（设备科）", response_model=ApiResponse[OrderDetail])
def dispatch(order_id: int, body: DispatchIn, db: DbSession, user: DeviceAdmin):
    return ok(_detail(db, order_service.dispatch(db, user, order_id, body), user), "派单成功")


@router.post("/{order_id}/reject", summary="驳回（设备科，须填写意见）", response_model=ApiResponse[OrderDetail])
def reject(order_id: int, body: ReasonIn, db: DbSession, user: DeviceAdmin):
    return ok(_detail(db, order_service.reject(db, user, order_id, body.reason), user), "已驳回")


@router.post("/{order_id}/resubmit", summary="驳回后修改并重新提交（报修人）", response_model=ApiResponse[OrderDetail])
def resubmit(
    order_id: int, db: DbSession, user: Reporter,
    device_id: Annotated[int, Form()],
    fault_desc: FaultDesc,
    urgency: Annotated[Urgency, Form()] = Urgency.NORMAL,
    keep_photos: Annotated[bool, Form(description="是否保留原照片")] = True,
    photos: Photos = [],  # noqa: B006
):
    order = order_service.resubmit(db, user, order_id, device_id, fault_desc, urgency, photos, keep_photos)
    return ok(_detail(db, order, user), "已重新提交，等待设备科派单")


@router.post("/{order_id}/take", summary="接单（维修工本人）", response_model=ApiResponse[OrderDetail])
def take(order_id: int, db: DbSession, user: Repairer, body: TakeIn | None = None):
    return ok(_detail(db, order_service.take(db, user, order_id, body.remark if body else None), user), "接单成功")


@router.post("/{order_id}/complete", summary="完工提交（维修工本人）", response_model=ApiResponse[OrderDetail])
def complete(order_id: int, body: CompleteIn, db: DbSession, user: Repairer):
    return ok(_detail(db, order_service.complete(db, user, order_id, body), user), "已提交完工，等待验收")


@router.post("/{order_id}/evaluate", summary="验收通过并评价，工单归档（报修人）", response_model=ApiResponse[OrderDetail])
def evaluate(order_id: int, body: EvaluateIn, db: DbSession, user: Reporter):
    return ok(_detail(db, order_service.evaluate(db, user, order_id, body), user), "验收完成，工单已归档")


@router.post("/{order_id}/accept-fail", summary="验收不通过，退回维修（报修人）", response_model=ApiResponse[OrderDetail])
def accept_fail(order_id: int, body: ReasonIn, db: DbSession, user: Reporter):
    return ok(_detail(db, order_service.accept_fail(db, user, order_id, body.reason), user), "已退回维修工返修")
