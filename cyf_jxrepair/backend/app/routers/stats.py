from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbSession, require_roles
from app.core.enums import UserRole
from app.core.response import ApiResponse, ok
from app.models import User
from app.schemas import DurationOut, MonthlyOut, NameValue, RankingItem, SummaryOut
from app.services import stat_service

router = APIRouter(prefix="/api/stats", tags=["统计看板"])

Viewer = Annotated[User, Depends(require_roles(UserRole.DEVICE_ADMIN, UserRole.DEPT_ADMIN))]


@router.get("/summary", summary="看板指标卡", response_model=ApiResponse[SummaryOut])
def summary(db: DbSession, user: Viewer):
    return ok(stat_service.summary(db, user))


@router.get("/monthly", summary="月度工单量", response_model=ApiResponse[MonthlyOut])
def monthly(db: DbSession, user: Viewer, months: Annotated[int, Query(ge=3, le=12)] = 6):
    return ok(stat_service.monthly(db, user, months))


@router.get("/status", summary="工单状态分布", response_model=ApiResponse[list[NameValue]])
def status(db: DbSession, user: Viewer):
    return ok(stat_service.status_distribution(db, user))


@router.get("/duration", summary="平均处理时长（按设备类别）", response_model=ApiResponse[DurationOut])
def duration(db: DbSession, user: Viewer):
    return ok(stat_service.avg_duration(db, user))


@router.get("/device-ranking", summary="设备故障排行", response_model=ApiResponse[list[RankingItem]])
def device_ranking(db: DbSession, user: Viewer, limit: Annotated[int, Query(ge=3, le=20)] = 10):
    return ok(stat_service.device_ranking(db, user, limit))
