from fastapi import APIRouter

from app.core.config import settings
from app.core.enums import FAULT_CATEGORIES, DeviceStatus, OrderStatus, Urgency, UserRole
from app.core.response import ApiResponse, ok

router = APIRouter(prefix="/api/meta", tags=["基础数据"])


@router.get("/options", summary="枚举选项（状态、角色、紧急程度等），前端下拉框统一从这里取",
            response_model=ApiResponse[dict])
def options():
    return ok({
        "app_name": settings.app_name,
        "order_status": OrderStatus.options(),
        "roles": UserRole.options(),
        "urgency": Urgency.options(),
        "device_status": DeviceStatus.options(),
        "fault_categories": list(FAULT_CATEGORIES),
        "upload": {"max_mb": settings.upload_max_mb, "max_count": settings.upload_max_count,
                   "accept": ["image/jpeg", "image/png"]},
    })
