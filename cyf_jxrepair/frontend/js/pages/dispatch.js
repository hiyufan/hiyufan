// 设备科派单中心：待派单 / 待接单 / 已驳回 三个视图，卡片上展示 AI 摘要
import { orderCard } from "../components/order-card.js";
import { runAction } from "../components/order-actions.js";
import { renderPager } from "../components/pager.js";
import { api } from "../core/http.js";
import { icon } from "../core/icons.js";
import { mountLayout } from "../core/layout.js";
import { $, debounce, emptyState, showError } from "../core/ui.js";

await mountLayout({ active: "dispatch", title: "派单" });

const TABS = [
  { key: "PENDING", label: "待派单", actions: [{ value: "DISPATCH", label: "派单" }, { value: "REJECT", label: "驳回" }] },
  { key: "ASSIGNED", label: "已派单待接单", actions: [] },
  { key: "REJECTED", label: "已驳回", actions: [] },
];
const state = { status: "PENDING", keyword: "", urgency: "", page: 1, size: 9 };
let currentItems = [];

$("#searchBox").insertAdjacentHTML("afterbegin", icon("search"));

async function loadTabs() {
  const counts = await api.get("/api/orders/status-counts");
  $("#tabs").innerHTML = TABS.map((t) => `
    <button class="tab ${t.key === state.status ? "active" : ""}" data-status="${t.key}">${t.label}
      <span class="count num">${counts[t.key]}</span></button>`).join("");
}

async function loadCards() {
  $("#cards").innerHTML = '<div class="panel-body"><div class="skeleton"></div></div>'.repeat(3);
  try {
    const page = await api.get("/api/orders", {
      status: state.status, keyword: state.keyword.trim(), urgency: state.urgency, page: state.page, size: state.size,
    });
    currentItems = page.items;
    // 待派单视图额外获取 AI 摘要（故障类型 + 风险等级）
    let summaries = {};
    if (state.status === "PENDING" && page.items.length) {
      const cards = await api.get("/api/ai/summaries", { status: "PENDING", limit: 20 });
      summaries = Object.fromEntries(cards.map((c) => [c.order_id, c]));
    }
    const tab = TABS.find((t) => t.key === state.status);
    // 紧急、超期的排在前面，方便优先处理
    const sorted = [...page.items].sort((a, b) => (b.is_overdue - a.is_overdue)
      || (b.urgency === "HIGH") - (a.urgency === "HIGH"));
    $("#cards").innerHTML = sorted.length
      ? sorted.map((o) => orderCard(o, { actions: tab.actions, summary: summaries[o.id] })).join("")
      : emptyState(state.status === "PENDING" ? "没有待派单的工单" : "暂无数据", state.status === "PENDING" ? "新的报修会出现在这里" : "", "checkCircle");
    renderPager($("#pager"), page, (p) => { state.page = p; loadCards(); });
  } catch (err) {
    $("#cards").innerHTML = emptyState("加载失败", err.message, "alert");
    showError(err);
  }
}

const refresh = () => Promise.all([loadTabs(), loadCards()]).catch(showError);

$("#tabs").addEventListener("click", (e) => {
  const tab = e.target.closest(".tab");
  if (!tab) return;
  state.status = tab.dataset.status;
  state.page = 1;
  refresh();
});
$("#keyword").addEventListener("input", debounce((e) => { state.keyword = e.target.value; state.page = 1; loadCards(); }, 400));
$("#urgency").addEventListener("change", (e) => { state.urgency = e.target.value; state.page = 1; loadCards(); });
$("#cards").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;
  const order = currentItems.find((o) => o.id === Number(btn.closest("[data-id]").dataset.id));
  runAction(btn.dataset.action, order, refresh);
});

refresh();
