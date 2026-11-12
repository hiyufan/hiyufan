from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbSession, Pagination, require_roles
from app.core.enums import UserRole
from app.core.response import ApiResponse, PageResult, ok
from app.models import User
from app.schemas import DeptOut, RepairerLoad, UserCreateIn, UserOut, UserStatusIn, UserUpdateIn
from app.services import user_service

router = APIRouter(prefix="/api", tags=["用户管理"])

UserManager = Annotated[User, Depends(require_roles(UserRole.DEVICE_ADMIN, UserRole.DEPT_ADMIN))]
DeviceAdmin = Annotated[User, Depends(require_roles(UserRole.DEVICE_ADMIN))]


@router.get("/users", summary="用户列表（分页 + 关键词 + 角色筛选）", response_model=ApiResponse[PageResult[UserOut]])
def list_users(
    db: DbSession, operator: UserManager, page: Pagination,
    keyword: Annotated[str | None, Query(max_length=30, description="账号/姓名/手机号")] = None,
    role: UserRole | None = None,
    dept_id: int | None = None,
):
    return ok(user_service.list_users(db, operator, page, keyword, role, dept_id))


@router.post("/users", summary="新增用户", response_model=ApiResponse[UserOut])
def create_user(body: UserCreateIn, db: DbSession, operator: UserManager):
    return ok(user_service.create_user(db, operator, body), "用户已创建")


@router.put("/users/{user_id}", summary="编辑用户", response_model=ApiResponse[UserOut])
def update_user(user_id: int, body: UserUpdateIn, db: DbSession, operator: UserManager):
    return ok(user_service.update_user(db, operator, user_id, body), "用户已更新")


@router.patch("/users/{user_id}/status", summary="启用 / 停用用户", response_model=ApiResponse[UserOut])
def set_status(user_id: int, body: UserStatusIn, db: DbSession, operator: UserManager):
    user = user_service.set_user_active(db, operator, user_id, body.is_active)
    return ok(user, "已启用" if body.is_active else "已停用")


@router.post("/users/{user_id}/reset-password", summary="重置密码为 123456", response_model=ApiResponse[None])
def reset_password(user_id: int, db: DbSession, operator: UserManager):
    user_service.reset_password(db, operator, user_id)
    return ok(message="密码已重置为 123456")


@router.get("/repairers", summary="维修工列表及当前负载（派单用）", response_model=ApiResponse[list[RepairerLoad]])
def repairers(
    db: DbSession, _: DeviceAdmin,
    category: Annotated[str | None, Query(description="故障大类，匹配擅长方向的排在前面")] = None,
):
    return ok(user_service.repairers_with_load(db, category))


@router.get("/depts", summary="部门列表", response_model=ApiResponse[list[DeptOut]])
def depts(db: DbSession):
    return ok([DeptOut.model_validate(d) for d in user_service.list_depts(db)])
