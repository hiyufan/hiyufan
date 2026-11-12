// 工单详情：按纸质《设备报修维修单》排版，已归档 / 已驳回盖章；下方为流转记录表
// 操作按钮完全由后端返回的 actions 决定（与状态机同一份规则）
import { actionButtons, runAction } from "../components/order-actions.js";
import { api, assetUrl } from "../core/http.js";
import { mountLayout } from "../core/layout.js";
import { $, duration, emptyState, esc, fmtTime, showError, statusTag, urgencyTag } from "../core/ui.js";

const id = Number(new URLSearchParams(location.search).get("id"));
await mountLayout({ active: "orders", title: "工单详情" });
$("#backBtn").addEventListener("click", (e) => {
  if (history.length > 1 && document.referrer.includes(location.host)) {
    e.preventDefault();
    history.back();
  }
});

const STEPS = [
  { label: "提交", time: "created_at" },
  { label: "派单", time: "dispatched_at" },
  { label: "接单", time: "taken_at" },
  { label: "完工", time: "completed_at" },
  { label: "验收归档", time: "archived_at" },
];
const STATUS_STEP = { PENDING: 1, REJECTED: 1, ASSIGNED: 2, REPAIRING: 3, TO_ACCEPT: 4, ARCHIVED: 5 };
const STATUS_LABEL = { PENDING: "待派单", ASSIGNED: "待接单", REPAIRING: "维修中", TO_ACCEPT: "待验收", ARCHIVED: "已归档", REJECTED: "已驳回" };

function steps(o) {
  const current = STATUS_STEP[o.status];
  return STEPS.map((s, i) => {
    const n = i + 1;
    let cls = n < current || o.status === "ARCHIVED" ? "done" : n === current ? "current" : "";
    let label = s.label;
    if (o.status === "REJECTED" && n === 2) { cls = "failed"; label = "驳回"; }
    return `<div class="step ${cls}"><b>${n} · ${label}</b><span class="time">${o[s.time] ? fmtTime(o[s.time]) : "—"}</span></div>`;
  }).join("");
}

function stamp(o) {
  if (o.status === "ARCHIVED") return `<div class="stamp">已归档<small>${fmtTime(o.archived_at, true).slice(0, 10)}</small></div>`;
  if (o.status === "REJECTED") return '<div class="stamp">驳回<small>设备科</small></div>';
  return "";
}

function renderDocket(o) {
  const d = o.device;
  const ev = o.evaluation;
  const photos = o.photo_urls.length
    ? `<div class="photo-grid">${o.photo_urls.map((u) => `<a href="${esc(assetUrl(u))}" target="_blank" rel="noopener"><img src="${esc(assetUrl(u))}" alt="现场照片" loading="lazy"></a>`).join("")}</div>`
    : '<span class="subtle">未上传</span>';
  const repairRows = o.repairer ? `
      <dt>维修工</dt><dd>${esc(o.repairer.real_name)} <span class="subtle">${esc(o.repairer.phone || "")}</span></dd>
      <dt>派单人</dt><dd>${o.dispatcher ? esc(o.dispatcher.real_name) : "—"}</dd>
      <dt>响应用时</dt><dd class="num">${duration(o.created_at, o.taken_at)}</dd>
      <dt>维修用时</dt><dd class="num">${duration(o.taken_at, o.completed_at)}</dd>
      <dt>故障类别</dt><dd class="span">${o.fault_category ? esc(o.fault_category) : '<span class="subtle">完工时由维修工确认</span>'}</dd>
      <dt>处理结果</dt><dd class="span">${o.repair_result ? esc(o.repair_result) : '<span class="subtle">维修中</span>'}</dd>` : "";
  const evalRows = ev ? `
      <div class="docket-section">验收</div>
      <dt>满意度</dt><dd><span class="score">${ev.score}</span> / 5</dd>
      <dt>验收时间</dt><dd class="num">${fmtTime(ev.created_at, true)}</dd>
      <dt>评价</dt><dd class="span">${esc(ev.comment || "—")}</dd>` : "";

  $("#docket").innerHTML = `
    ${stamp(o)}
    <div class="docket-title">
      <h2>设备报修维修单</h2>
      <div class="docket-no"><span>编号</span>${esc(o.order_no)}</div>
    </div>
    <div class="steps">${steps(o)}</div>
    <dl class="docket-grid" style="margin:0">
      <dt>当前状态</dt><dd>${statusTag(o.status, o.status_label)} ${o.is_overdue ? '<span class="flag-overdue">超期 48h+</span>' : ""}</dd>
      <dt>紧急程度</dt><dd>${urgencyTag(o.urgency, o.urgency_label)}</dd>
      ${o.status === "REJECTED" ? `<dt>驳回意见</dt><dd class="span" style="color:var(--red)">${esc(o.reject_reason)}</dd>` : ""}
      <div class="docket-section">报修</div>
      <dt>设备名称</dt><dd><b>${esc(d.device_name)}</b></dd>
      <dt>设备编号</dt><dd class="mono">${esc(d.device_code)}</dd>
      <dt>设备类别</dt><dd>${esc(d.category)}</dd>
      <dt>安装位置</dt><dd>${esc(d.factory_area)} · ${esc(d.location)}</dd>
      <dt>报修人</dt><dd>${esc(o.reporter.real_name)} <span class="subtle">${esc(o.reporter.phone || "")}</span></dd>
      <dt>报修时间</dt><dd class="num">${fmtTime(o.created_at, true)}</dd>
      <dt>故障描述</dt><dd class="span" style="white-space:pre-wrap">${esc(o.fault_desc)}</dd>
      <dt>现场照片</dt><dd class="span">${photos}</dd>
      ${o.repairer ? '<div class="docket-section">维修</div>' : ""}
      ${repairRows}
      ${evalRows}
    </dl>
    ${o.actions.length ? `<div class="docket-actions">${actionButtons(o.actions)}</div>` : ""}`;
}

function renderLogs(o) {
  $("#logCount").textContent = `共 ${o.logs.length} 条`;
  $("#logs").innerHTML = o.logs.map((lg) => `
    <tr>
      <td class="time">${fmtTime(lg.created_at, true)}</td>
      <td class="act-${esc(lg.action)}"><b>${esc(lg.action_label)}</b></td>
      <td>${esc(lg.operator.real_name)}<div class="subtle">${esc(lg.operator_role)}</div></td>
      <td class="subtle">${lg.from_status ? `${STATUS_LABEL[lg.from_status] || lg.from_status} → ` : ""}${STATUS_LABEL[lg.to_status] || lg.to_status}</td>
      <td style="white-space:normal;min-width:240px">${esc(lg.content)}</td>
    </tr>`).join("");
}

async function renderSummary() {
  try {
    const s = await api.get(`/api/orders/${id}/summary`);
    $("#summaryEngine").textContent = s.engine === "llm" ? "大模型生成" : "本地规则生成";
    const risk = s.fields["风险等级"];
    $("#summary").innerHTML = `
      <p style="line-height:1.75">${esc(s.text)}</p>
      <dl class="docket-grid" style="grid-template-columns:80px minmax(0,1fr);margin-top:12px;border:1px solid var(--rule)">
        <dt>故障类型</dt><dd>${esc(s.fields["故障类型"])}</dd>
        <dt>风险</dt><dd><span class="risk risk-${esc(risk)}">${esc(risk)}</span></dd>
        <dt>处理时长</dt><dd class="num">${esc(s.fields["处理时长"])}</dd>
      </dl>`;
  } catch (err) {
    $("#summary").innerHTML = `<span class="subtle">${esc(err.message)}</span>`;
  }
}

async function renderSimilar(o) {
  try {
    const hits = await api.get("/api/ai/knowledge", { q: o.fault_desc, exclude_order_id: o.id, top_k: 3 });
    $("#similarCard").classList.toggle("hidden", !hits.length);
    $("#similar").innerHTML = hits.map((h) => `
      <a class="case" href="order-detail.html?id=${h.order_id}">
        <b>${esc(h.device_name)}：${esc(h.fault_desc)}</b>
        <span>处理：${esc(h.repair_result)}</span></a>`).join("");
  } catch { /* 相似案例非核心，失败时不打扰用户 */ }
}

async function load() {
  try {
    const o = await api.get(`/api/orders/${id}`);
    document.title = `${o.order_no} · CYF捷修云`;
    renderDocket(o);
    renderLogs(o);
    renderSummary();
    renderSimilar(o);
    $("#docket").onclick = (e) => {
      const btn = e.target.closest("[data-action]");
      if (btn) runAction(btn.dataset.action, o, load);
    };
  } catch (err) {
    $("#docket").innerHTML = emptyState("无法查看该工单", err.message, "alert");
    showError(err);
  }
}

if (!id) location.replace("orders.html");
else load();
