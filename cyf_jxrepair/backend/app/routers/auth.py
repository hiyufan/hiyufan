from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.core.response import ApiResponse, ok
from app.schemas import LoginIn, LoginOut, PasswordChangeIn, UserOut
from app.services import user_service

router = APIRouter(prefix="/api/auth", tags=["登录鉴权"])


@router.post("/login", summary="登录（返回 token 与角色）", response_model=ApiResponse[LoginOut])
def login(body: LoginIn, db: DbSession):
    return ok(user_service.login(db, body.username, body.password), "登录成功")


@router.get("/me", summary="获取当前登录用户", response_model=ApiResponse[UserOut])
def me(user: CurrentUser):
    return ok(UserOut.of(user))


@router.put("/password", summary="修改本人密码", response_model=ApiResponse[None])
def change_password(body: PasswordChangeIn, user: CurrentUser, db: DbSession):
    user_service.change_password(db, user, body)
    return ok(message="密码已修改，请重新登录")


@router.post("/logout", summary="退出登录", response_model=ApiResponse[None])
def logout(_: CurrentUser):
    # JWT 无状态，服务端无需记录；前端清除本地 token 即完成退出
    return ok(message="已退出登录")
