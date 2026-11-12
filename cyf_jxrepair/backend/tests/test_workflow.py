"""状态机单元测试：不依赖数据库，直接验证越权与非法流转都会被拦截。"""
from dataclasses import dataclass

import pytest

from app.core.enums import OrderAction, OrderStatus, UserRole
from app.core.exceptions import Conflict, Forbidden
from app.services.workflow import TRANSITIONS, available_actions, ensure_can


@dataclass
class FakeUser:
    id: int
    role: UserRole


@dataclass
class FakeOrder:
    status: OrderStatus
    reporter_id: int = 1
    repairer_id: int | None = 3


EMPLOYEE = FakeUser(1, UserRole.EMPLOYEE)
OTHER_EMPLOYEE = FakeUser(9, UserRole.EMPLOYEE)
ADMIN = FakeUser(2, UserRole.DEVICE_ADMIN)
REPAIRER = FakeUser(3, UserRole.REPAIRER)
OTHER_REPAIRER = FakeUser(4, UserRole.REPAIRER)


@pytest.mark.parametrize(("status", "action", "user"), [
    (OrderStatus.PENDING, OrderAction.DISPATCH, ADMIN),
    (OrderStatus.PENDING, OrderAction.REJECT, ADMIN),
    (OrderStatus.REJECTED, OrderAction.RESUBMIT, EMPLOYEE),
    (OrderStatus.ASSIGNED, OrderAction.TAKE, REPAIRER),
    (OrderStatus.REPAIRING, OrderAction.COMPLETE, REPAIRER),
    (OrderStatus.TO_ACCEPT, OrderAction.ACCEPT, EMPLOYEE),
    (OrderStatus.TO_ACCEPT, OrderAction.ACCEPT_FAIL, EMPLOYEE),
])
def test_legal_transitions(status, action, user):
    ensure_can(FakeOrder(status), action, user)


@pytest.mark.parametrize(("status", "action", "user"), [
    (OrderStatus.PENDING, OrderAction.DISPATCH, EMPLOYEE),        # 普通员工不能派单
    (OrderStatus.TO_ACCEPT, OrderAction.ACCEPT, REPAIRER),        # 维修工不能验收
    (OrderStatus.ASSIGNED, OrderAction.TAKE, OTHER_REPAIRER),     # 不能接别人的单
    (OrderStatus.TO_ACCEPT, OrderAction.ACCEPT, OTHER_EMPLOYEE),  # 不能验收别人的报修
    (OrderStatus.REJECTED, OrderAction.RESUBMIT, OTHER_EMPLOYEE),
])
def test_forbidden(status, action, user):
    with pytest.raises(Forbidden):
        ensure_can(FakeOrder(status), action, user)


@pytest.mark.parametrize(("status", "action", "user"), [
    (OrderStatus.ASSIGNED, OrderAction.DISPATCH, ADMIN),          # 不能重复派单
    (OrderStatus.PENDING, OrderAction.COMPLETE, REPAIRER),        # 跳步完工
    (OrderStatus.REPAIRING, OrderAction.ACCEPT, EMPLOYEE),        # 未完工就验收
])
def test_illegal_state(status, action, user):
    with pytest.raises(Conflict):
        ensure_can(FakeOrder(status), action, user)


@pytest.mark.parametrize("action", list(TRANSITIONS))
def test_archived_is_frozen(action):
    with pytest.raises(Conflict, match="已归档"):
        ensure_can(FakeOrder(OrderStatus.ARCHIVED), action, ADMIN)


def test_available_actions_drive_buttons():
    assert available_actions(FakeOrder(OrderStatus.PENDING), ADMIN) == [OrderAction.DISPATCH, OrderAction.REJECT]
    assert available_actions(FakeOrder(OrderStatus.PENDING), EMPLOYEE) == []
    assert available_actions(FakeOrder(OrderStatus.ASSIGNED), REPAIRER) == [OrderAction.TAKE]
    assert available_actions(FakeOrder(OrderStatus.ASSIGNED), OTHER_REPAIRER) == []
    assert set(available_actions(FakeOrder(OrderStatus.TO_ACCEPT), EMPLOYEE)) == {
        OrderAction.ACCEPT, OrderAction.ACCEPT_FAIL}
    assert available_actions(FakeOrder(OrderStatus.ARCHIVED), ADMIN) == []
