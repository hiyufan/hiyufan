from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession, PageParams, require_roles
from app.core.enums import OrderStatus, UserRole
from app.core.response import ApiResponse, ok
from app.models import User
from app.schemas import AlertHandleOut, AlertOut, DiagnoseIn, DiagnoseOut, KnowledgeHit, SummaryCard
from app.services import alert_service, order_service
from app.services.ai import diagnosis, summary
from app.services.ai.knowledge import knowledge_base

router = APIRouter(prefix="/api/ai", tags=["AI 智能拓展"])

DeviceAdmin = Annotated[User, Depends(require_roles(UserRole.DEVICE_ADMIN))]
Viewer = Annotated[User, Depends(require_roles(UserRole.DEVICE_ADMIN, UserRole.DEPT_ADMIN))]


@router.get("/engine", summary="当前 AI 引擎（本地离线 / 大模型）", response_model=ApiResponse[dict])
def engine(_: CurrentUser):
    return ok({"llm_enabled": settings.llm_enabled, "llm_model": settings.llm_model if settings.llm_enabled else None})


@router.post("/diagnose", summary="① 故障智能诊断", response_model=ApiResponse[DiagnoseOut])
def diagnose(body: DiagnoseIn, db: DbSession, _: CurrentUser):
    return ok(diagnosis.diagnose(db, body.fault_desc, body.device_id))


@router.get("/knowledge", summary="② 维修知识库检索（相似故障）", response_model=ApiResponse[list[KnowledgeHit]])
def knowledge(
    db: DbSession, _: CurrentUser,
    q: Annotated[str, Query(min_length=2, max_length=100, description="故障关键词或描述")],
    exclude_order_id: int | None = None,
    top_k: Annotated[int, Query(ge=1, le=20)] = 8,
):
    return ok(knowledge_base.search(db, q, top_k=top_k, exclude_order_id=exclude_order_id))


@router.get("/summaries", summary="③ 工单智能摘要（批量，派单页/看板用）", response_model=ApiResponse[list[SummaryCard]])
def summaries(
    db: DbSession, user: Viewer,
    status: Annotated[list[OrderStatus] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 6,
):
    page = order_service.list_orders(db, user, PageParams(page=1, size=limit), statuses=status)
    return ok([summary.build(db, order_service.get_scoped(db, user, o.id)) for o in page.items])


@router.get("/alerts", summary="④ 超期工单预警列表", response_model=ApiResponse[list[AlertOut]])
def alerts(db: DbSession, _: Viewer):
    return ok(alert_service.list_open(db))


@router.post("/alerts/scan", summary="④ 立即执行一次超期扫描", response_model=ApiResponse[dict])
def scan(db: DbSession, _: DeviceAdmin):
    result = alert_service.scan(db)
    return ok(result, f"扫描完成：新增 {result['created']} 条，自动解除 {result['resolved']} 条")


@router.post("/alerts/{alert_id}/handle", summary="④ 一键处理超期预警", response_model=ApiResponse[AlertHandleOut])
def handle(alert_id: int, db: DbSession, user: DeviceAdmin):
    result = alert_service.handle(db, user, alert_id)
    return ok(result, result.handle_note)
