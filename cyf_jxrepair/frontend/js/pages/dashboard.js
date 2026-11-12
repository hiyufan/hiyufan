// 统计看板：指标卡 + 超期预警 + 4 类图表 + AI 摘要
// 配色经过色盲安全校验：系列 1 青 #0d9488、系列 2 橙 #eb6834；单一指标的图只用一种颜色
import { api } from "../core/http.js";
import { icon } from "../core/icons.js";
import { mountLayout } from "../core/layout.js";
import { $, confirmDialog, emptyState, esc, showError, toast, withLoading } from "../core/ui.js";

const user = await mountLayout({ active: "dashboard", title: "统计看板" });
const isAdmin = user.role === "DEVICE_ADMIN";

const C = {
  s1: "#0d9488",
  s2: "#eb6834",
  ink: "#334452",
  muted: "#8a99a5",
  grid: "#eef2f4",
  axis: "#e3e8ec",
};
const charts = {};

$("#pageTitle").textContent = isAdmin ? "全厂统计看板" : `${user.dept_name} · 统计看板`;
$("#pageDesc").textContent = isAdmin ? "全部厂区数据，实时来自数据库聚合" : "本部门员工提交的工单数据";
$("#refreshBtn").innerHTML = `${icon("refresh", "icon-sm")}刷新`;

// ------------------------------------------------------------ 指标卡
function renderStats(s) {
  const cards = [
    { label: "工单总数", value: s.total, unit: "单", icon: "file", tone: "brand", foot: "累计全部报修" },
    { label: "待派单", value: s.pending, unit: "单", icon: "inbox", tone: "amber", foot: s.open_alerts ? `${s.open_alerts} 张超期待处理` : "无超期工单" },
    { label: "处理中", value: s.in_progress + s.to_accept, unit: "单", icon: "hammer", tone: "blue", foot: `待接单/维修中 ${s.in_progress} · 待验收 ${s.to_accept}` },
    { label: "本月归档", value: s.archived_this_month, unit: "单", icon: "checkCircle", tone: "green",
      foot: s.avg_score ? `平均满意度 ${s.avg_score.toFixed(1)} / 5` : "暂无评价" },
  ];
  $("#statCards").innerHTML = cards.map((c) => `
    <div class="card stat-card tone-${c.tone}">
      <div class="label">${icon(c.icon)}${c.label}</div>
      <div class="value">${c.value}<small>${c.unit}</small></div>
      <div class="foot">${esc(c.foot)}</div>
    </div>`).join("");
}

// ------------------------------------------------------------ 超期预警
async function loadAlerts() {
  const alerts = await api.get("/api/ai/alerts");
  const panel = $("#alertPanel");
  panel.classList.toggle("hidden", !alerts.length);
  if (!alerts.length) return;
  $("#alertHead").innerHTML = `${icon("bell")}<h3>超期工单预警</h3>
    <span class="tag tag-overdue">${alerts.length} 张</span>
    <span class="extra subtle">超过 48 小时未派单或未完工${isAdmin ? "，可一键处理" : ""}</span>`;
  $("#alertList").innerHTML = alerts.map((a) => `
    <div class="alert-row" data-id="${a.id}">
      <span class="hours">${a.overdue_hours}<small>小时</small></span>
      <div><a href="order-detail.html?id=${a.order_id}" class="mono">${esc(a.order_no)}</a>
        <span class="muted"> · ${esc(a.device_name)}</span>
        <div class="subtle">${esc(a.alert_label)} · 当前${esc(a.status_label)}</div></div>
      <span class="tag ${a.alert_type === "DISPATCH_TIMEOUT" ? "st-PENDING" : "st-REPAIRING"}">${esc(a.alert_label)}</span>
      ${isAdmin ? `<button class="btn btn-sm btn-primary" data-handle="${a.id}" data-type="${a.alert_type}">
        ${icon(a.alert_type === "DISPATCH_TIMEOUT" ? "zap" : "bell", "icon-sm")}${a.alert_type === "DISPATCH_TIMEOUT" ? "一键派单" : "一键催办"}</button>` : "<span></span>"}
    </div>`).join("");
}

$("#alertList").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-handle]");
  if (!btn) return;
  const dispatch = btn.dataset.type === "DISPATCH_TIMEOUT";
  const ok = await confirmDialog({
    title: dispatch ? "一键派单" : "一键催办",
    message: dispatch
      ? "系统将根据故障类型匹配擅长该方向、当前负载最低的维修工并自动派单，确定吗？"
      : "将向负责该工单的维修工发出催办，并记录在流转日志中。",
    confirmText: dispatch ? "自动派单" : "发送催办",
  });
  if (!ok) return;
  await withLoading(btn, async () => {
    try {
      const r = await api.post(`/api/ai/alerts/${btn.dataset.handle}/handle`);
      toast(r.handle_note);
      loadAll();
    } catch (err) { showError(err); }
  });
});

// ------------------------------------------------------------ 图表
const baseAxis = {
  axisLine: { lineStyle: { color: C.axis } },
  axisTick: { show: false },
  axisLabel: { color: C.muted, fontSize: 12 },
  splitLine: { lineStyle: { color: C.grid } },
};
const tooltip = (extra = {}) => ({
  trigger: "axis", axisPointer: { type: "shadow", shadowStyle: { color: "rgba(13,148,136,.06)" } },
  backgroundColor: "#fff", borderColor: C.axis, textStyle: { color: C.ink, fontSize: 12 },
  extraCssText: "box-shadow:0 6px 16px rgba(15,28,36,.12);border-radius:8px;", ...extra,
});
const legend = { top: 0, right: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: C.ink } };
// 柱子：细、末端 4px 圆角、相邻柱之间留 2px 白边
const bar = (color, horizontal = false) => ({
  type: "bar", barMaxWidth: horizontal ? 14 : 18, barGap: "20%",
  itemStyle: { color, borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0], borderColor: "#fff", borderWidth: 1 },
  emphasis: { focus: "series" },
});

function chart(id) {
  if (!window.echarts) throw new Error("echarts.min.js 未加载");
  charts[id] ??= echarts.init(document.getElementById(id), null, { renderer: "svg" });
  return charts[id];
}

function noData(id, text = "暂无数据") {
  charts[id]?.dispose();
  delete charts[id];
  $(`#${id}`).innerHTML = emptyState(text);
}

function renderMonthly(d) {
  chart("chartMonthly").setOption({
    tooltip: tooltip(), legend,
    grid: { left: 36, right: 8, top: 36, bottom: 24 },
    xAxis: { type: "category", data: d.months.map((m) => `${Number(m.slice(5))}月`), ...baseAxis, splitLine: { show: false } },
    yAxis: { type: "value", minInterval: 1, ...baseAxis, axisLine: { show: false } },
    series: [
      { name: "提交", data: d.submitted, ...bar(C.s1) },
      { name: "归档", data: d.archived, ...bar(C.s2) },
    ],
  });
}

function renderStatus(list) {
  const total = list.reduce((a, b) => a + b.value, 0);
  $("#statusTotal").textContent = `共 ${total} 单`;
  if (!total) return noData("chartStatus");
  // 各状态由坐标轴文字区分，所以只用一种颜色表示数量，不靠颜色区分类别
  chart("chartStatus").setOption({
    tooltip: tooltip({ formatter: (p) => `${p[0].name}：<b>${p[0].value}</b> 单（${((p[0].value / total) * 100).toFixed(1)}%）` }),
    grid: { left: 56, right: 48, top: 8, bottom: 8 },
    xAxis: { type: "value", show: false, max: (v) => v.max * 1.1 },
    yAxis: { type: "category", inverse: true, data: list.map((i) => i.name), ...baseAxis, axisLine: { show: false },
      axisLabel: { color: C.ink, fontSize: 13 } },
    series: [{ ...bar(C.s1, true), barMaxWidth: 18, data: list.map((i) => i.value),
      label: { show: true, position: "right", color: C.ink, formatter: (p) => `${p.value}` } }],
  });
}

function renderDuration(d) {
  $("#durationAvg").textContent = d.overall_hours != null ? `平均全程 ${d.overall_hours} 小时` : "";
  if (!d.categories.length) return noData("chartDuration", "暂无已归档工单");
  chart("chartDuration").setOption({
    tooltip: tooltip({ valueFormatter: (v) => `${v} 小时` }), legend,
    grid: { left: 72, right: 16, top: 36, bottom: 24 },
    xAxis: { type: "value", name: "小时", nameTextStyle: { color: C.muted }, ...baseAxis },
    yAxis: { type: "category", inverse: true, data: d.categories, ...baseAxis, axisLine: { show: false },
      axisLabel: { color: C.ink, fontSize: 12 } },
    series: [
      { name: "响应（提交→接单）", data: d.response_hours, ...bar(C.s1, true) },
      { name: "维修（接单→完工）", data: d.repair_hours, ...bar(C.s2, true) },
    ],
  });
}

function renderRanking(list) {
  if (!list.length) return noData("chartRanking");
  chart("chartRanking").setOption({
    tooltip: tooltip({ formatter: (p) => `${p[0].name}<br><span style="color:${C.muted}">${list[p[0].dataIndex].device_code} · ${list[p[0].dataIndex].category}</span><br>故障 <b>${p[0].value}</b> 次` }),
    grid: { left: 96, right: 36, top: 8, bottom: 8 },
    xAxis: { type: "value", show: false, minInterval: 1 },
    yAxis: { type: "category", inverse: true, data: list.map((i) => i.device_name), ...baseAxis, axisLine: { show: false },
      axisLabel: { color: C.ink, fontSize: 12, width: 84, overflow: "truncate" } },
    series: [{ ...bar(C.s1, true), data: list.map((i) => i.count),
      label: { show: true, position: "right", color: C.ink } }],
  });
}

// ------------------------------------------------------------ AI 摘要
async function loadSummaries() {
  $("#summaryHead").innerHTML = `${icon("sparkles", "icon-sm")}<h3>AI 工单摘要</h3><span class="extra subtle">最新 6 张处理中的工单</span>`;
  const cards = await api.get("/api/ai/summaries", { status: ["PENDING", "ASSIGNED", "REPAIRING", "TO_ACCEPT"], limit: 6 });
  $("#summaryList").innerHTML = cards.length ? cards.map((c) => `
    <div class="summary-card" data-id="${c.order_id}" tabindex="0" role="link">
      <h4><span class="mono">${esc(c.order_no)}</span><span class="tag plain">${esc(c.fields["当前状态"])}</span></h4>
      <p>${esc(c.text)}</p>
      <div class="kv"><span class="chip">${esc(c.fields["故障类型"])}</span>
        <span class="risk-chip risk-${esc(c.fields["风险等级"])}">风险 ${esc(c.fields["风险等级"])}</span></div>
    </div>`).join("") : emptyState("没有处理中的工单");
}
$("#summaryList").addEventListener("click", (e) => {
  const card = e.target.closest("[data-id]");
  if (card) location.href = `order-detail.html?id=${card.dataset.id}`;
});

async function loadAll() {
  const months = $("#months").value;
  try {
    const [summary, monthly, status, dur, ranking] = await Promise.all([
      api.get("/api/stats/summary"),
      api.get("/api/stats/monthly", { months }),
      api.get("/api/stats/status"),
      api.get("/api/stats/duration"),
      api.get("/api/stats/device-ranking"),
    ]);
    renderStats(summary);
    renderMonthly(monthly);
    renderStatus(status);
    renderDuration(dur);
    renderRanking(ranking);
    await Promise.all([loadAlerts(), loadSummaries()]);
  } catch (err) {
    showError(err);
  }
}

$("#months").addEventListener("change", loadAll);
$("#refreshBtn").addEventListener("click", (e) => withLoading(e.currentTarget, loadAll));
window.addEventListener("resize", () => Object.values(charts).forEach((c) => c.resize()));

loadAll();
