"""工单状态机：所有"谁能在什么状态下做什么"的规则集中在 TRANSITIONS 一张表里。

    待派单 PENDING ──派单──▶ 待接单 ASSIGNED ──接单──▶ 维修中 REPAIRING ──完工──▶ 待验收 TO_ACCEPT ──验收通过──▶ 已归档 ARCHIVED
       │  ▲                                                ▲                         │
     驳回 │ 重新提交                                          └──────验收不通过─────────┘
       ▼  │
    已驳回 REJECTED

接口层只需调用 ensure_can(order, action, user)；前端按钮由 available_actions() 决定，
前后端共用同一份规则，不会出现"按钮能点但接口拒绝"或反过来的情况。
"""
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.core.enums import OrderAction, OrderStatus, UserRole
from app.core.exceptions import Conflict, Forbidden


class Owner(str, Enum):
    """操作人与工单的归属关系要求。"""

    ANY = "ANY"            # 只看角色
    REPORTER = "REPORTER"  # 必须是报修人本人
    REPAIRER = "REPAIRER"  # 必须是被指派的维修工本人


@dataclass(frozen=True, slots=True)
class Transition:
    action: OrderAction
    sources: frozenset[OrderStatus]
    target: OrderStatus
    roles: frozenset[UserRole]
    owner: Owner = Owner.ANY


_REPORTER_ROLES = frozenset({UserRole.EMPLOYEE, UserRole.DEPT_ADMIN})

TRANSITIONS: dict[OrderAction, Transition] = {
    t.action: t
    for t in (
        Transition(OrderAction.DISPATCH, frozenset({OrderStatus.PENDING}), OrderStatus.ASSIGNED,
                   frozenset({UserRole.DEVICE_ADMIN})),
        Transition(OrderAction.REJECT, frozenset({OrderStatus.PENDING}), OrderStatus.REJECTED,
                   frozenset({UserRole.DEVICE_ADMIN})),
        Transition(OrderAction.RESUBMIT, frozenset({OrderStatus.REJECTED}), OrderStatus.PENDING,
                   _REPORTER_ROLES, Owner.REPORTER),
        Transition(OrderAction.TAKE, frozenset({OrderStatus.ASSIGNED}), OrderStatus.REPAIRING,
                   frozenset({UserRole.REPAIRER}), Owner.REPAIRER),
        Transition(OrderAction.COMPLETE, frozenset({OrderStatus.REPAIRING}), OrderStatus.TO_ACCEPT,
                   frozenset({UserRole.REPAIRER}), Owner.REPAIRER),
        Transition(OrderAction.ACCEPT, frozenset({OrderStatus.TO_ACCEPT}), OrderStatus.ARCHIVED,
                   _REPORTER_ROLES, Owner.REPORTER),
        Transition(OrderAction.ACCEPT_FAIL, frozenset({OrderStatus.TO_ACCEPT}), OrderStatus.REPAIRING,
                   _REPORTER_ROLES, Owner.REPORTER),
    )
}

TERMINAL_STATUSES = frozenset({OrderStatus.ARCHIVED})


class _OrderLike(Protocol):
    status: OrderStatus
    reporter_id: int
    repairer_id: int | None


class _UserLike(Protocol):
    id: int
    role: UserRole


def _owner_ok(rule: Transition, order: _OrderLike, user: _UserLike) -> bool:
    if rule.owner is Owner.REPORTER:
        return order.reporter_id == user.id
    if rule.owner is Owner.REPAIRER:
        return order.repairer_id == user.id
    return True


def ensure_can(order: _OrderLike, action: OrderAction, user: _UserLike) -> Transition:
    """校验顺序：终态 → 角色 → 归属 → 当前状态。任何一步不满足即拦截。"""
    rule = TRANSITIONS[action]
    if order.status in TERMINAL_STATUSES:
        raise Conflict("工单已归档，不允许再变更")
    if user.role not in rule.roles:
        raise Forbidden(f"{user.role.label}无权执行「{action.label}」")
    if not _owner_ok(rule, order, user):
        who = "报修人本人" if rule.owner is Owner.REPORTER else "被指派的维修工本人"
        raise Forbidden(f"仅{who}可执行「{action.label}」")
    if order.status not in rule.sources:
        expected = "、".join(s.label for s in rule.sources)
        raise Conflict(f"当前状态为「{order.status.label}」，仅「{expected}」状态可执行「{action.label}」")
    return rule


def available_actions(order: _OrderLike, user: _UserLike) -> list[OrderAction]:
    """当前用户对该工单可执行的操作列表，供前端渲染按钮。"""
    if order.status in TERMINAL_STATUSES:
        return []
    return [
        action for action, rule in TRANSITIONS.items()
        if order.status in rule.sources and user.role in rule.roles and _owner_ok(rule, order, user)
    ]
