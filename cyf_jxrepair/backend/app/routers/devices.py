from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, Pagination, require_roles
from app.core.enums import DeviceStatus, UserRole
from app.core.response import ApiResponse, PageResult, ok
from app.models import User
from app.schemas import DeviceIn, DeviceOut
from app.services import device_service

router = APIRouter(prefix="/api/devices", tags=["设备管理"])

DeviceAdmin = Annotated[User, Depends(require_roles(UserRole.DEVICE_ADMIN))]


@router.get("", summary="设备台账（分页 + 关键词 + 类别/状态筛选）", response_model=ApiResponse[PageResult[DeviceOut]])
def list_devices(
    db: DbSession, _: CurrentUser, page: Pagination,
    keyword: Annotated[str | None, Query(max_length=30, description="编号/名称/位置/型号")] = None,
    category: str | None = None,
    status: DeviceStatus | None = None,
    dept_id: int | None = None,
):
    return ok(device_service.list_devices(db, page, keyword, category, status, dept_id))


@router.get("/options", summary="报修可选设备（不含已报废）", response_model=ApiResponse[list[DeviceOut]])
def options(db: DbSession, _: CurrentUser):
    return ok(device_service.device_options(db))


@router.get("/categories", summary="设备类别列表", response_model=ApiResponse[list[str]])
def categories(db: DbSession, _: CurrentUser):
    return ok(device_service.categories(db))


@router.post("", summary="新增设备", response_model=ApiResponse[DeviceOut])
def create_device(body: DeviceIn, db: DbSession, _: DeviceAdmin):
    return ok(device_service.create_device(db, body), "设备已新增")


@router.put("/{device_id}", summary="编辑设备", response_model=ApiResponse[DeviceOut])
def update_device(device_id: int, body: DeviceIn, db: DbSession, _: DeviceAdmin):
    return ok(device_service.update_device(db, device_id, body), "设备已更新")


@router.delete("/{device_id}", summary="删除设备（有报修记录时禁止删除）", response_model=ApiResponse[None])
def delete_device(device_id: int, db: DbSession, _: DeviceAdmin):
    device_service.delete_device(db, device_id)
    return ok(message="设备已删除")
