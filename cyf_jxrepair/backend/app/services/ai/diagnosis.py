"""拓展功能 1：故障智能诊断。

本地方案：fault_knowledge 表中每条规则有若干关键词，故障描述命中的关键词越多、越长，得分越高；
取得分最高的 3 条作为可能原因，并按故障大类推荐擅长该方向、手头工单最少的维修工，辅助派单。
大模型方案：配置 LLM_API_KEY 后优先调用大模型，失败自动降级为本地方案。
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, FaultKnowledge
from app.schemas import DiagnoseOut, DiagnosisItem
from app.services import user_service
from app.services.ai import llm

# 命中即提示安全风险的关键词
_SAFETY_WORDS = ("冒烟", "起火", "火花", "焦糊", "烧焦", "漏电", "触电", "光栅", "急停", "保护失灵", "爆", "人员")
_STOP_WORDS = ("停机", "无法启动", "不能用", "全线", "停产")

_SYSTEM_PROMPT = (
    "你是制造企业设备科的资深维修工程师。根据设备信息和故障描述，给出最可能的 1-3 个故障原因。"
    "category 只能从【电气故障、机械故障、液压故障、气动故障、数控系统、润滑冷却】中选择。"
    '只输出 JSON：{"items":[{"category":"","cause":"","suggestion":"","confidence":0.0}]}'
)


def assess_risk(text: str) -> tuple[str, list[str]]:
    tips = []
    if hits := [w for w in _SAFETY_WORDS if w in text]:
        tips.append(f"涉及安全隐患（{'、'.join(hits)}），请立即断电挂牌并疏散人员")
    if hits := [w for w in _STOP_WORDS if w in text]:
        tips.append(f"可能影响生产（{'、'.join(hits)}），建议优先派单")
    level = "高" if any("安全" in t for t in tips) else ("中" if tips else "低")
    return level, tips


def _local(db: Session, text: str) -> list[DiagnosisItem]:
    scored = []
    for rule in db.scalars(select(FaultKnowledge)):
        matched = [k for k in rule.keyword_list if k in text]
        if matched:
            score = sum(len(k) for k in matched)
            scored.append((score, rule, matched))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        DiagnosisItem(category=rule.category, cause=rule.cause, suggestion=rule.suggestion,
                      confidence=round(min(0.95, score / (score + 4)), 2), matched_keywords=matched)
        for score, rule, matched in scored[:3]
    ]


def _via_llm(text: str, device: Device | None) -> list[DiagnosisItem] | None:
    device_info = f"{device.category}/{device.device_name}/{device.model or ''}" if device else "未指定"
    data = llm.chat_json(_SYSTEM_PROMPT, f"设备：{device_info}\n故障描述：{text}")
    if not data:
        return None
    try:
        return [
            DiagnosisItem(category=i["category"], cause=i["cause"], suggestion=i["suggestion"],
                          confidence=float(i.get("confidence", 0.6)), matched_keywords=[])
            for i in data.get("items", [])[:3]
        ] or None
    except (KeyError, TypeError, ValueError):
        return None


def diagnose(db: Session, fault_desc: str, device_id: int | None = None) -> DiagnoseOut:
    text = fault_desc.strip()
    device = db.get(Device, device_id) if device_id else None

    items, engine = _via_llm(text, device), "llm"
    if items is None:
        items, engine = _local(db, text), "local-kb"

    level, tips = assess_risk(text)
    if not items:
        tips.append("知识库未匹配到已知故障模式，建议补充更具体的现象（声音、气味、报警号等）")

    best_category = items[0].category if items else None
    repairers = user_service.repairers_with_load(db, best_category)[:3]
    return DiagnoseOut(engine=engine, items=items, risk_level=level, risk_tips=tips,
                       recommended_repairers=repairers)


def top_category(db: Session, fault_desc: str) -> str | None:
    """只取最可能的故障大类（摘要、自动派单复用，始终走本地规则，保证速度）。"""
    items = _local(db, fault_desc)
    return items[0].category if items else None
