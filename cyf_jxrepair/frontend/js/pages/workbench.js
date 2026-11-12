// 维修工工作台：待接单 / 维修中 / 待验收 / 已归档，卡片上直接接单、完工
import { orderCard } from "../components/order-card.js";
import { runAction } from "../components/order-actions.js";
import { renderPager } from "../components/pager.js";
import { api } from "../core/http.js";
import { icon } from "../core/icons.js";
import { mountLayout } from "../core/layout.js";
import { $, emptyState, esc, showError } from "../core/ui.js";

const user = await mountLayout({ active: "workbench", title: "维修工作台" });

const TABS = [
  { key: "ASSIGNED", label: "待接单", icon: "inbox", tone: "amber", actions: [{ value: "TAKE", label: "接单" }], empty: "暂无新派工单" },
  { key: "REPAIRING", label: "维修中", icon: "hammer", tone: "blue", actions: [{ value: "COMPLETE", label: "完工提交" }], empty: "没有进行中的维修" },
  { key: "TO_ACCEPT", label: "待验收", icon: "clock", tone: "violet", actions: [], empty: "没有等待验收的工单" },
  { key: "ARCHIVED", label: "已归档", icon: "checkCircle", tone: "green", actions: [], empty: "还没有归档的工单" },
];
const state = { status: "ASSIGNED", page: 1, size: 9 };
let items = [];

const hour = new Date().getHours();
$("#hello").textContent = `${hour < 12 ? "早上好" : hour < 18 ? "下午好" : "晚上好"}，${user.real_name}`;

async function loadStats() {
  const counts = await api.get("/api/orders/status-counts");
  $("#stats").innerHTML = TABS.map((t) => `
    <div class="card stat-card tone-${t.tone}">
      <div class="label">${icon(t.icon)}${t.label}</div>
      <div class="value">${counts[t.key]}<small>单</small></div>
    </div>`).join("");
  $("#tabs").innerHTML = TABS.map((t) => `
    <button class="tab ${t.key === state.status ? "active" : ""}" data-status="${t.key}">${t.label}<span class="count num">${counts[t.key]}</span></button>`).join("");
  return counts;
}

async function loadCards() {
  const tab = TABS.find((t) => t.key === state.status);
  try {
    const page = await api.get("/api/orders", { status: state.status, page: state.page, size: state.size });
    items = page.items;
    $("#cards").innerHTML = items.length
      ? items.map((o) => orderCard(o, { actions: tab.actions })).join("")
      : `<div style="grid-column:1/-1">${emptyState(tab.empty, "", "checkCircle")}</div>`;
    renderPager($("#pager"), page, (p) => { state.page = p; loadCards(); });
  } catch (err) {
    $("#cards").innerHTML = `<div style="grid-column:1/-1">${emptyState("加载失败", esc(err.message), "alert")}</div>`;
  }
}

const refresh = () => Promise.all([loadStats(), loadCards()]).catch(showError);

$("#tabs").addEventListener("click", (e) => {
  const tab = e.target.closest(".tab");
  if (!tab) return;
  state.status = tab.dataset.status;
  state.page = 1;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
  loadCards();
});
$("#cards").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;
  const order = items.find((o) => o.id === Number(btn.closest("[data-id]").dataset.id));
  runAction(btn.dataset.action, order, refresh);
});

// 首次进入：没有待接单但有维修中的工单时，默认打开"维修中"
async function init() {
  const counts = await api.get("/api/orders/status-counts");
  if (!counts.ASSIGNED && counts.REPAIRING) state.status = "REPAIRING";
  await refresh();
}

init().catch(showError);
