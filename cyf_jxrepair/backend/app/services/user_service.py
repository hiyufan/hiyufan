"""用户与部门管理。部门管理员只能管理本部门的普通员工，设备科管理员可管理全部用户。"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import PageParams
from app.core.enums import ACTIVE_STATUSES, UserRole
from app.core.exceptions import BizError, Conflict, Forbidden, NotFound, Unauthorized
from app.core.response import PageResult, page_of
from app.core.security import create_token, hash_password, verify_password
from app.models import Dept, RepairOrder, User
from app.schemas import (
    LoginOut,
    PasswordChangeIn,
    RepairerLoad,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
)


# ------------------------------------------------------------------ 登录
def login(db: Session, username: str, password: str) -> LoginOut:
    user = db.scalar(select(User).where(User.username == username))
    # 账号不存在与密码错误给出相同提示，避免被用来探测有效账号
    if user is None or not verify_password(password, user.password_hash):
        raise Unauthorized("账号或密码错误")
    if not user.is_active:
        raise Forbidden("账号已被停用，请联系管理员")
    return LoginOut(
        token=create_token(user.id, user.role.value),
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserOut.of(user),
    )


def change_password(db: Session, user: User, data: PasswordChangeIn) -> None:
    if not verify_password(data.old_password, user.password_hash):
        raise BizError("原密码不正确")
    if data.old_password == data.new_password:
        raise BizError("新密码不能与原密码相同")
    user.password_hash = hash_password(data.new_password)
    db.commit()


# ------------------------------------------------------------------ 权限范围
def _assert_manageable(operator: User, target_role: UserRole, target_dept_id: int) -> None:
    if operator.role is UserRole.DEVICE_ADMIN:
        return
    if operator.role is UserRole.DEPT_ADMIN:
        if target_dept_id != operator.dept_id:
            raise Forbidden("部门管理员只能管理本部门人员")
        if target_role is not UserRole.EMPLOYEE:
            raise Forbidden("部门管理员只能管理普通员工账号")
        return
    raise Forbidden()


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("用户不存在")
    return user


# ------------------------------------------------------------------ 用户管理
def list_users(
    db: Session, operator: User, page: PageParams,
    keyword: str | None, role: UserRole | None, dept_id: int | None,
) -> PageResult[UserOut]:
    stmt = select(User)
    if operator.role is UserRole.DEPT_ADMIN:
        stmt = stmt.where(User.dept_id == operator.dept_id)
    elif dept_id:
        stmt = stmt.where(User.dept_id == dept_id)
    if role:
        stmt = stmt.where(User.role == role)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(User.username.like(like), User.real_name.like(like), User.phone.like(like)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(User.id).offset(page.offset).limit(page.size)).all()
    return page_of([UserOut.of(u) for u in rows], total, page.page, page.size)


def create_user(db: Session, operator: User, data: UserCreateIn) -> UserOut:
    _assert_manageable(operator, data.role, data.dept_id)
    if db.get(Dept, data.dept_id) is None:
        raise NotFound("部门不存在")
    if db.scalar(select(User.id).where(User.username == data.username)):
        raise Conflict(f"账号 {data.username} 已存在")
    user = User(
        username=data.username, real_name=data.real_name, phone=data.phone, role=data.role,
        dept_id=data.dept_id, password_hash=hash_password(data.password),
        skills=",".join(data.skills) if data.role is UserRole.REPAIRER and data.skills else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.of(user)


def update_user(db: Session, operator: User, user_id: int, data: UserUpdateIn) -> UserOut:
    user = _get_user(db, user_id)
    _assert_manageable(operator, user.role, user.dept_id)
    changes = data.model_dump(exclude_unset=True)
    new_role = changes.get("role", user.role)
    new_dept = changes.get("dept_id", user.dept_id)
    _assert_manageable(operator, new_role, new_dept)  # 修改后的结果也必须在管理范围内
    if user.id == operator.id and new_role != operator.role:
        raise BizError("不能修改自己的角色")
    if "skills" in changes:
        changes["skills"] = ",".join(changes["skills"] or []) or None
    for key, value in changes.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return UserOut.of(user)


def set_user_active(db: Session, operator: User, user_id: int, active: bool) -> UserOut:
    user = _get_user(db, user_id)
    _assert_manageable(operator, user.role, user.dept_id)
    if user.id == operator.id:
        raise BizError("不能停用自己的账号")
    if not active and user.role is UserRole.REPAIRER:
        busy = db.scalar(select(func.count()).where(
            RepairOrder.repairer_id == user.id, RepairOrder.status.in_(ACTIVE_STATUSES)))
        if busy:
            raise Conflict(f"该维修工还有 {busy} 张未完成工单，请先改派后再停用")
    user.is_active = active
    db.commit()
    return UserOut.of(user)


def reset_password(db: Session, operator: User, user_id: int) -> None:
    user = _get_user(db, user_id)
    _assert_manageable(operator, user.role, user.dept_id)
    user.password_hash = hash_password("123456")
    db.commit()


def list_depts(db: Session) -> list[Dept]:
    return list(db.scalars(select(Dept).order_by(Dept.id)))


# ------------------------------------------------------------------ 维修工负载（派单用）
def repairers_with_load(db: Session, category: str | None = None) -> list[RepairerLoad]:
    """返回启用中的维修工及其手头工单数。匹配擅长方向的排前面，同组内负载低的排前面。"""
    load = (
        select(RepairOrder.repairer_id, func.count().label("cnt"))
        .where(RepairOrder.status.in_(ACTIVE_STATUSES))
        .group_by(RepairOrder.repairer_id)
        .subquery()
    )
    rows = db.execute(
        select(User, func.coalesce(load.c.cnt, 0))
        .outerjoin(load, load.c.repairer_id == User.id)
        .where(User.role == UserRole.REPAIRER, User.is_active.is_(True))
    ).all()
    result = [
        RepairerLoad(
            id=u.id, real_name=u.real_name, skills=u.skill_list, active_orders=int(cnt),
            matched=bool(category and category in u.skill_list),
        )
        for u, cnt in rows
    ]
    result.sort(key=lambda r: (not r.matched, r.active_orders, r.id))
    return result
