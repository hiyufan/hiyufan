"""拓展功能 3：工单智能摘要。

把一张工单的故障描述、处理结果、时间线压缩成结构化摘要卡片，供派单页、统计页快速浏览。
本地方案基于规则抽取；配置大模型后由大模型生成一句话摘要，结构化字段仍由规则保证准确。
"""
from sqlalchemy.orm import Session

from app.models import RepairOrder
from app.schemas import SummaryCard
from app.services.ai import diagnosis, llm
from app.services.ai.text import first_sentence

_SYSTEM_PROMPT = '你是工单摘要助手。用不超过 40 个汉字概括工单，只输出 JSON：{"text": ""}'


def _hours(start, end) -> str:
    if not (start and end):
        return "—"
    hours = (end - start).total_seconds() / 3600
    return f"{hours:.1f} 小时" if hours >= 1 else f"{hours * 60:.0f} 分钟"


def build(db: Session, order: RepairOrder, use_llm: bool = False) -> SummaryCard:
    """use_llm 只在查看单张工单时开启；列表批量生成摘要始终走本地规则，避免逐条请求大模型拖慢页面。"""
    device = order.device
    # 维修工已确认的故障类别最可靠；还没完工的工单用诊断结果
    category = order.fault_category or diagnosis.top_category(db, order.fault_desc, exclude_order_id=order.id)
    risk, _ = diagnosis.assess_risk(order.fault_desc)  # 与故障诊断复用同一套风险词规则
    symptom = first_sentence(order.fault_desc)
    result = first_sentence(order.repair_result or "", 40) if order.repair_result else "尚未处理"

    fields = {
        "设备": f"{device.device_name}（{device.device_code}）",
        "位置": f"{device.dept.factory_area} · {device.location}",
        "故障类型": category or "待判定",
        "风险等级": risk,
        "现象": symptom,
        "处理": result,
        "当前状态": order.status.label,
        "处理时长": _hours(order.created_at, order.archived_at or order.completed_at),
    }
    text = f"【{device.device_name}】{symptom}，" + (f"初判为{category}" if category else "故障类型待人工判定")
    text += f"；处理：{result}" if order.repair_result else "；尚未处理"

    engine = "local-rule"
    data = llm.chat_json(_SYSTEM_PROMPT, "\n".join(f"{k}：{v}" for k, v in fields.items())) if use_llm else None
    if data and isinstance(data.get("text"), str) and data["text"].strip():
        text, engine = data["text"].strip(), "llm"

    return SummaryCard(order_id=order.id, order_no=order.order_no, engine=engine,
                       title=f"{order.order_no} · {device.device_name}", fields=fields, text=text)
