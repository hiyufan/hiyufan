"""通用依赖：当前登录用户、角色守卫、分页参数。"""
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import UserRole
from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import decode_token
from app.models import User

_bearer = HTTPBearer(auto_error=False, description="登录接口返回的 token")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise Unauthorized("请先登录")
    user = db.get(User, decode_token(credentials.credentials))
    if user is None or not user.is_active:
        raise Unauthorized("账号不存在或已被停用")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """角色守卫：接口级别的粗粒度权限控制。工单状态的细粒度校验在 workflow 中完成。"""
    allowed = frozenset(roles)

    def _guard(user: CurrentUser) -> User:
        if user.role not in allowed:
            names = "、".join(r.label for r in roles)
            raise Forbidden(f"仅{names}可执行该操作")
        return user

    return _guard


class PageParams(BaseModel):
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def page_params(
    page: Annotated[int, Query(ge=1, description="页码，从 1 开始")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="每页条数，最大 100")] = 10,
) -> PageParams:
    return PageParams(page=page, size=size)


Pagination = Annotated[PageParams, Depends(page_params)]
