"""业务枚举：数据库存英文编码，界面展示中文标签，两者在这里一处维护。"""
from enum import Enum


class LabeledEnum(str, Enum):
    """带中文标签的字符串枚举，成员写法：CODE = "CODE", "中文标签"。"""

    label: str

    def __new__(cls, value: str, label: str = ""):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label or value
        return obj

    def __str__(self) -> str:  # 兼容 Python 3.10（3.11 起才有 StrEnum）
        return self.value

    @classmethod
    def options(cls) -> list[dict[str, str]]:
        return [{"value": m.value, "label": m.label} for m in cls]


class UserRole(LabeledEnum):
    EMPLOYEE = "EMPLOYEE", "普通员工"
    DEPT_ADMIN = "DEPT_ADMIN", "部门管理员"
    DEVICE_ADMIN = "DEVICE_ADMIN", "设备科管理员"
    REPAIRER = "REPAIRER", "维修工"


class OrderStatus(LabeledEnum):
    PENDING = "PENDING", "待派单"
    ASSIGNED = "ASSIGNED", "待接单"
    REPAIRING = "REPAIRING", "维修中"
    TO_ACCEPT = "TO_ACCEPT", "待验收"
    ARCHIVED = "ARCHIVED", "已归档"
    REJECTED = "REJECTED", "已驳回"


class OrderAction(LabeledEnum):
    SUBMIT = "SUBMIT", "提交报修"
    DISPATCH = "DISPATCH", "派单"
    REJECT = "REJECT", "驳回"
    RESUBMIT = "RESUBMIT", "重新提交"
    TAKE = "TAKE", "接单"
    COMPLETE = "COMPLETE", "完工提交"
    ACCEPT = "ACCEPT", "验收通过"
    ACCEPT_FAIL = "ACCEPT_FAIL", "验收不通过"
    ARCHIVE = "ARCHIVE", "归档"
    URGE = "URGE", "超期催办"


class Urgency(LabeledEnum):
    LOW = "LOW", "一般"
    NORMAL = "NORMAL", "较急"
    HIGH = "HIGH", "紧急"


class DeviceStatus(LabeledEnum):
    NORMAL = "NORMAL", "正常"
    REPAIRING = "REPAIRING", "维修中"
    SCRAPPED = "SCRAPPED", "已报废"


class AlertType(LabeledEnum):
    DISPATCH_TIMEOUT = "DISPATCH_TIMEOUT", "超时未派单"
    REPAIR_TIMEOUT = "REPAIR_TIMEOUT", "超时未完工"


# 故障大类：知识库规则、维修工擅长方向、完工时确认的故障类别共用这一套分类
FAULT_CATEGORIES = ("电气故障", "机械故障", "液压故障", "气动故障", "数控系统", "润滑冷却")

# 工单仍在处理中的状态（用于维修工负载、设备状态联动、超期扫描）
ACTIVE_STATUSES = frozenset({OrderStatus.ASSIGNED, OrderStatus.REPAIRING, OrderStatus.TO_ACCEPT})
