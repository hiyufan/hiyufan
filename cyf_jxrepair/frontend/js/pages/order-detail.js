// 工单详情：进度条 + 基本信息 + 照片 + 维修结果/评价 + AI 摘要 + 流转时间线 + 相似案例
// 操作按钮完全由后端返回的 actions 决定（与状态机同一份规则）
import { actionButtons, runAction } from "../components/order-actions.js";
import { api, assetUrl } from "../core/http.js";
import { icon } from "../core/icons.js";
import { mountLayout } from "../core/layout.js";
import { $, duration, emptyState, esc, fmtTime, showError, statusTag, urgencyTag } from "../core/ui.js";

const id = Number(new URLSearchParams(location.search).get("id"));
await mountLayout({ active: "orders", title: "工单详情" });
$("#backBtn").innerHTML = `${icon("arrowLeft", "icon-sm")}返回`;
$("#backBtn").addEventListener("click", (e) => {
  if (history.length > 1 && document.referrer.includes(location.host)) {
    e.preventDefault();
    history.back();
  }
});

const STEPS = [
  { label: "提交报修", time: "created_at" },
  { label: "设备科派单", time: "dispatched_at" },
  { label: "维修工接单", time: "taken_at" },
  { label: "完工提交", time: "completed_at" },
  { label: "验收归档", time: "archived_at" },
];
const STATUS_STEP = { PENDING: 1, REJECTED: 1, ASSIGNED: 2, REPAIRING: 3, TO_ACCEPT: 4, ARCHIVED: 5 };

function renderHead(o) {
  $("#head").innerHTML = `
    <div>
      <h2><span class="mono">${esc(o.order_no)}</span>${statusTag(o.status, o.status_label)}${urgencyTag(o.urgency, o.urgency_label)}
        ${o.is_overdue ? '<span class="tag tag-overdue">超期</span>' : ""}</h2>
      <div class="meta">
        <span>${icon("user", "icon-sm")} ${esc(o.reporter.real_name)} 提交于 ${fmtTime(o.created_at, true)}</span>
        ${o.archived_at ? `<span>${icon("clock", "icon-sm")} 全程用时 ${duration(o.created_at, o.archived_at)}</span>` : ""}
      </div>
    </div>
    <div class="btn-group">${actionButtons(o.actions)}</div>`;
}

function renderSteps(o) {
  const current = STATUS_STEP[o.status];
  $("#steps").innerHTML = STEPS.map((s, i) => {
    const n = i + 1;
    let cls = n < current || (n === current && o.status === "ARCHIVED") ? "done" : n === current ? "current" : "";
    if (o.status === "REJECTED" && n === 2) cls = "failed";
    const label = o.status === "REJECTED" && n === 2 ? "已驳回" : s.label;
    return `<div class="step ${cls}"><div class="node">${cls === "done" ? icon("check", "icon-sm") : cls === "failed" ? icon("x", "icon-sm") : n}</div>
      ${label}<span class="time num">${o[s.time] ? fmtTime(o[s.time]) : ""}</span></div>`;
  }).join("");
}

function renderInfo(o) {
  const d = o.device;
  const photos = o.photo_urls.length
    ? `<div class="photo-grid">${o.photo_urls.map((u) => `<a href="${esc(assetUrl(u))}" target="_blank" rel="noopener"><img src="${esc(assetUrl(u))}" alt="现场照片" loading="lazy"></a>`).join("")}</div>`
    : '<span class="subtle">未上传照片</span>';
  $("#info").innerHTML = `
    ${o.status === "REJECTED" ? `<div class="alert alert-danger" style="margin-bottom:16px">${icon("xCircle", "icon-sm")}<span><b>驳回意见：</b>${esc(o.reject_reason)}</span></div>` : ""}
    <dl class="desc-list">
      <dt>报修设备</dt><dd><b>${esc(d.device_name)}</b> <span class="mono subtle">${esc(d.device_code)}</span> <span class="chip">${esc(d.category)}</span></dd>
      <dt>安装位置</dt><dd>${esc(d.factory_area)} · ${esc(d.location)}</dd>
      <dt>报修人</dt><dd>${esc(o.reporter.real_name)} <span class="subtle">${esc(o.reporter.phone || "")}</span></dd>
      <dt>故障描述</dt><dd style="white-space:pre-wrap">${esc(o.fault_desc)}</dd>
      <dt>现场照片</dt><dd>${photos}</dd>
    </dl>`;
}

function renderResult(o) {
  if (!o.repairer && o.status !== "REJECTED") {
    $("#result").innerHTML = emptyState("等待设备科派单", "派单后将在这里显示维修进度", "clock");
    return;
  }
  if (o.status === "REJECTED") {
    $("#resultCard").classList.add("hidden");
    return;
  }
  const ev = o.evaluation;
  $("#result").innerHTML = `
    <dl class="desc-list">
      <dt>维修工</dt><dd>${esc(o.repairer.real_name)} <span class="subtle">${esc(o.repairer.phone || "")}</span></dd>
      <dt>派单人</dt><dd>${o.dispatcher ? esc(o.dispatcher.real_name) : "—"}</dd>
      <dt>响应用时</dt><dd>${duration(o.created_at, o.taken_at)}<span class="subtle">（提交 → 接单）</span></dd>
      <dt>维修用时</dt><dd>${duration(o.taken_at, o.completed_at)}<span class="subtle">（接单 → 完工）</span></dd>
      <dt>处理结果</dt><dd>${o.repair_result ? esc(o.repair_result) : '<span class="subtle">维修中</span>'}</dd>
      ${ev ? `<dt>验收评价</dt><dd><span class="stars-readonly">${"★".repeat(ev.score)}${"☆".repeat(5 - ev.score)}</span>
        <span class="subtle">${fmtTime(ev.created_at)}</span>${ev.comment ? `<div class="muted" style="margin-top:4px">${esc(ev.comment)}</div>` : ""}</dd>` : ""}
    </dl>`;
}

function renderTimeline(o) {
  $("#logCount").textContent = `${o.logs.length} 条`;
  $("#timeline").innerHTML = [...o.logs].reverse().map((lg) => `
    <div class="tl-item t-${esc(lg.action)}">
      <div class="tl-head"><b>${esc(lg.action_label)}</b><span class="subtle">${esc(lg.operator.real_name)} · ${esc(lg.operator_role)}</span></div>
      <div class="tl-body">${esc(lg.content)}</div>
      <div class="subtle num">${fmtTime(lg.created_at, true)}</div>
    </div>`).join("");
}

async function renderSummary() {
  try {
    const s = await api.get(`/api/orders/${id}/summary`);
    $("#summaryHead h3").innerHTML = `${icon("sparkles", "icon-sm")} AI 工单摘要`;
    $("#summaryEngine").textContent = s.engine === "llm" ? "大模型生成" : "本地规则生成";
    const risk = s.fields["风险等级"];
    $("#summary").innerHTML = `
      <p style="font-size:14px;line-height:1.7">${esc(s.text)}</p>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:12px">
        <span class="chip">${esc(s.fields["故障类型"])}</span>
        <span class="risk-chip risk-${esc(risk)}">风险 ${esc(risk)}</span>
        <span class="tag plain">${esc(s.fields["处理时长"])}</span>
      </div>`;
  } catch (err) {
    $("#summary").innerHTML = `<span class="subtle">${esc(err.message)}</span>`;
  }
}

async function renderSimilar(o) {
  try {
    const hits = await api.get("/api/ai/knowledge", { q: o.fault_desc, exclude_order_id: o.id, top_k: 3 });
    $("#similarCard").classList.toggle("hidden", !hits.length);
    $("#similar").innerHTML = hits.map((h) => `
      <a class="similar-item" href="order-detail.html?id=${h.order_id}">
        <b>${esc(h.device_name)} · ${esc(h.fault_desc)}</b>
        <span class="muted">处理：${esc(h.repair_result)}</span></a>`).join("");
  } catch { /* 相似案例非核心，失败时静默 */ }
}

async function load() {
  try {
    const o = await api.get(`/api/orders/${id}`);
    renderHead(o);
    renderSteps(o);
    renderInfo(o);
    renderResult(o);
    renderTimeline(o);
    renderSummary();
    renderSimilar(o);
    $("#head").onclick = (e) => {
      const btn = e.target.closest("[data-action]");
      if (btn) runAction(btn.dataset.action, o, load);
    };
  } catch (err) {
    $("#head").innerHTML = emptyState("无法查看该工单", err.message, "alert");
    $("#steps").innerHTML = "";
    showError(err);
  }
}

if (!id) location.replace("orders.html");
else load();
