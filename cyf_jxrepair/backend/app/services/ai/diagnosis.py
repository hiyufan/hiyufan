"""拓展功能 1：故障智能诊断 —— 规则推理 + 案例推理（CBR）混合。

两路证据各自给出"属于某故障类别"的置信度，再用 noisy-OR 合成：

1. 规则证据（专家经验）
   fault_knowledge 表每条规则有一组关键词。故障描述命中的关键词越多、越长，得分 s 越高，
   置信度 r = s / (s + 4)，即命中约 4 个字的关键词时 r = 0.5，之后增长逐渐放缓。

2. 案例证据（历史数据）—— 参考 Aamodt & Plaza (1994)
   "Case-Based Reasoning: Foundational Issues, Methodological Variations, and System Approaches"
   的 retrieve → reuse 两步：
   - retrieve：用 BM25 从已归档工单中找出最相似的 K 个案例，每个案例带有维修工完工时确认的故障类别；
   - reuse：按相似度加权投票，vote(c) = Σ sim(案例∈c) / Σ sim(全部案例)，
     再乘以可信度 min(1, 最高相似度 / 0.5)：最像的案例都不太像时，整体证据要打折。
   维修工每次完工都会确认故障类别，案例库随使用自动增长，诊断越用越准（CBR 中的 retain 步骤）。

3. 合成：P = 1 − (1 − r)(1 − c)
   noisy-OR 假设两路证据相互独立：任一路有把握结论就有把握，两路都支持时置信度更高。

可选：配置大模型后优先由大模型给出结论，失败时自动回到本地方案。
"""
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import FAULT_CATEGORIES
from app.models import Device, FaultKnowledge
from app.schemas import CaseRef, DiagnoseOut, DiagnosisItem
from app.services import user_service
from app.services.ai import llm
from app.services.ai.knowledge import Case, knowledge_base
from app.services.ai.text import expand_synonyms

K_CASES = 5               # 参与投票的相似案例数
CASE_MIN_MATCH = 0.12     # 低于该匹配度的案例不参与投票
CASE_FULL_MATCH = 0.5     # 最高相似度达到该值时，案例证据不打折
MIN_CONFIDENCE = 0.15     # 低于该置信度的类别不展示

# 命中即提示安全风险的关键词
_SAFETY_WORDS = ("冒烟", "起火", "火花", "焦糊", "烧焦", "漏电", "触电", "光栅", "急停", "保护失灵", "爆", "人员")
_STOP_WORDS = ("停机", "无法启动", "不能用", "全线", "停产")

_SYSTEM_PROMPT = (
    "你是制造企业设备科的资深维修工程师。根据设备信息和故障描述，给出最可能的 1-3 个故障原因。"
    f"category 只能从【{'、'.join(FAULT_CATEGORIES)}】中选择。"
    '只输出 JSON：{"items":[{"category":"","cause":"","suggestion":"","confidence":0.0}]}'
)


@dataclass
class _Evidence:
    rule_conf: float = 0.0
    rule: FaultKnowledge | None = None
    keywords: list[str] = field(default_factory=list)
    case_conf: float = 0.0
    cases: list[tuple[Case, float]] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return 1 - (1 - self.rule_conf) * (1 - self.case_conf)


def assess_risk(text: str) -> tuple[str, list[str]]:
    tips = []
    if hits := [w for w in _SAFETY_WORDS if w in text]:
        tips.append(f"涉及安全隐患（{'、'.join(hits)}），请立即断电挂牌并疏散人员")
    if hits := [w for w in _STOP_WORDS if w in text]:
        tips.append(f"可能影响生产（{'、'.join(hits)}），建议优先派单")
    level = "高" if any("安全" in t for t in tips) else ("中" if tips else "低")
    return level, tips


def _rule_evidence(db: Session, text: str, ev: dict[str, _Evidence]) -> None:
    for rule in db.scalars(select(FaultKnowledge)):
        matched = [k for k in rule.keyword_list if k in text]
        if not matched:
            continue
        s = sum(len(k) for k in matched)
        conf = s / (s + 4)
        e = ev[rule.category]
        if conf > e.rule_conf:  # 同一类别取最有把握的那条规则
            e.rule_conf, e.rule, e.keywords = conf, rule, matched


def _case_evidence(db: Session, text: str, ev: dict[str, _Evidence], exclude_order_id: int | None) -> None:
    hits = [(c, m) for c, m in knowledge_base.similar(db, text, top_k=K_CASES, min_match=CASE_MIN_MATCH,
                                                       exclude_order_id=exclude_order_id)
            if c.fault_category]
    if not hits:
        return
    total = sum(m for _, m in hits)
    reliability = min(1.0, hits[0][1] / CASE_FULL_MATCH)
    votes: dict[str, float] = defaultdict(float)
    for case, match in hits:
        votes[case.fault_category] += match
        ev[case.fault_category].cases.append((case, match))
    for category, weight in votes.items():
        ev[category].case_conf = min(0.9, weight / total * reliability)


def _to_item(category: str, e: _Evidence) -> DiagnosisItem:
    if e.rule:
        cause, suggestion = e.rule.cause, e.rule.suggestion
    else:  # 只有案例证据：直接复用最相似案例的处理方法（CBR 的 reuse）
        case = e.cases[0][0]
        cause = f"与历史案例 {case.order_no} 相似：{case.fault_desc}"
        suggestion = f"参考该案例处理：{case.repair_result}"
    return DiagnosisItem(
        category=category, cause=cause, suggestion=suggestion,
        confidence=round(min(0.97, e.confidence), 2),
        rule_confidence=round(e.rule_conf, 2), case_confidence=round(e.case_conf, 2),
        matched_keywords=e.keywords,
        evidence_cases=[CaseRef(order_id=c.order_id, order_no=c.order_no, similarity=round(m, 2))
                        for c, m in e.cases[:2]],
    )


def local_diagnose(db: Session, text: str, exclude_order_id: int | None = None, *,
                   use_cases: bool = True, use_synonyms: bool = True) -> list[DiagnosisItem]:
    """use_cases / use_synonyms 仅供 scripts/eval_diagnosis.py 做对比实验，业务调用保持默认。"""
    if use_synonyms:
        text = expand_synonyms(text)  # 口语说法先映射到标准术语，规则和案例两路都受益
    ev: dict[str, _Evidence] = defaultdict(_Evidence)
    _rule_evidence(db, text, ev)
    if use_cases:
        _case_evidence(db, text, ev, exclude_order_id)
    ranked = sorted(ev.items(), key=lambda kv: kv[1].confidence, reverse=True)
    return [_to_item(cat, e) for cat, e in ranked if e.confidence >= MIN_CONFIDENCE][:3]


def _via_llm(text: str, device: Device | None) -> list[DiagnosisItem] | None:
    device_info = f"{device.category}/{device.device_name}/{device.model or ''}" if device else "未指定"
    data = llm.chat_json(_SYSTEM_PROMPT, f"设备：{device_info}\n故障描述：{text}")
    if not data:
        return None
    try:
        items = [
            DiagnosisItem(category=i["category"], cause=i["cause"], suggestion=i["suggestion"],
                          confidence=float(i.get("confidence", 0.6)), matched_keywords=[])
            for i in data.get("items", [])[:3] if i.get("category") in FAULT_CATEGORIES
        ]
        return items or None
    except (KeyError, TypeError, ValueError):
        return None


def diagnose(db: Session, fault_desc: str, device_id: int | None = None) -> DiagnoseOut:
    text = fault_desc.strip()
    device = db.get(Device, device_id) if device_id else None

    items, engine = _via_llm(text, device), "llm"
    if items is None:
        items, engine = local_diagnose(db, text), "local-kb"

    level, tips = assess_risk(text)
    if not items:
        tips.append("知识库和历史案例都没有匹配，建议补充更具体的现象（声音、气味、报警号等）")

    best_category = items[0].category if items else None
    repairers = user_service.recommend_repairers(db, best_category)[:3]
    return DiagnoseOut(engine=engine, items=items, risk_level=level, risk_tips=tips,
                       recommended_repairers=repairers)


def top_category(db: Session, fault_desc: str, exclude_order_id: int | None = None) -> str | None:
    """只取最可能的故障类别（摘要、自动派单复用；始终走本地方案，保证速度）。"""
    items = local_diagnose(db, fault_desc, exclude_order_id)
    return items[0].category if items else None
