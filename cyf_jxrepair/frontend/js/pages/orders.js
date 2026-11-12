// 工单列表：状态页签 + 关键词搜索 + 紧急程度筛选 + 分页；筛选条件同步到地址栏，刷新或返回时保留
import { actionButtons, runAction } from "../components/order-actions.js";
import { renderPager } from "../components/pager.js";
import { api } from "../core/http.js";
import { icon } from "../core/icons.js";
import { mountLayout } from "../core/layout.js";
import { $, debounce, emptyState, esc, fmtTime, fromNow, showError, skeletonRows, statusTag, urgencyTag } from "../core/ui.js";

const TITLES = {
  EMPLOYEE: ["我的报修", "查看本人提交的全部报修记录；被驳回的工单可修改后重新提交"],
  DEPT_ADMIN: ["部门工单", "本部门员工提交的全部报修工单"],
  REPAIRER: ["我的工单", "指派给我的全部维修工单"],
  DEVICE_ADMIN: ["全部工单", "全厂报修工单，支持按状态、关键词检索"],
};
const TABS = [
  { key: "", label: "全部" },
  { key: "PENDING", label: "待派单" },
  { key: "ASSIGNED", label: "待接单" },
  { key: "REPAIRING", label: "维修中" },
  { key: "TO_ACCEPT", label: "待验收" },
  { key: "REJECTED", label: "已驳回" },
  { key: "ARCHIVED", label: "已归档" },
];
const COLS = 9;

const user = await mountLayout({ active: "orders", title: (u) => TITLES[u.role][0] });

const url = new URLSearchParams(location.search);
const state = {
  status: url.get("status") || "",
  keyword: url.get("keyword") || "",
  urgency: url.get("urgency") || "",
  page: Number(url.get("page")) || 1,
  size: 10,
};

$("#pageTitle").textContent = TITLES[user.role][0];
$("#pageDesc").textContent = TITLES[user.role][1];
$("#searchBox").insertAdjacentHTML("afterbegin", icon("search"));
$("#refreshBtn").innerHTML = `${icon("refresh", "icon-sm")}刷新`;
$("#keyword").value = state.keyword;
$("#urgency").value = state.urgency;
if (["EMPLOYEE", "DEPT_ADMIN"].includes(user.role)) {
  $("#newBtn").classList.remove("hidden");
  $("#newBtn").innerHTML = `${icon("plus", "icon-sm")}我要报修`;
}

function syncUrl() {
  const q = new URLSearchParams();
  Object.entries({ status: state.status, keyword: state.keyword, urgency: state.urgency })
    .forEach(([k, v]) => v && q.set(k, v));
  if (state.page > 1) q.set("page", state.page);
  history.replaceState(null, "", `${location.pathname}${q.toString() ? `?${q}` : ""}`);
}

async function loadCounts() {
  const counts = await api.get("/api/orders/status-counts");
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  $("#tabs").innerHTML = TABS.map((t) => `
    <button class="tab ${t.key === state.status ? "active" : ""}" role="tab" data-status="${t.key}">
      ${t.label}<span class="count num">${t.key ? counts[t.key] : total}</span></button>`).join("");
}

function row(o) {
  // 员工视角：被驳回的工单在列表中直接显示驳回原因
  const reject = o.status === "REJECTED" && o.reject_reason
    ? `<div class="subtle" style="color:var(--danger);margin-top:2px">驳回：${esc(o.reject_reason)}</div>` : "";
  const quick = o.status === "REJECTED" && o.reporter.id === user.id
    ? actionButtons([{ value: "RESUBMIT", label: "修改重提" }], "btn-sm") : "";
  return `
    <tr class="clickable" data-id="${o.id}">
      <td><span class="mono primary-text">${esc(o.order_no)}</span>
        ${o.is_overdue ? '<div style="margin-top:4px"><span class="tag tag-overdue">超期</span></div>' : ""}</td>
      <td><div class="primary-text">${esc(o.device.device_name)}</div><div class="subtle">${esc(o.device.factory_area)} · ${esc(o.device.location)}</div></td>
      <td class="wrap"><div class="desc ellipsis" title="${esc(o.fault_desc)}">${esc(o.fault_desc)}</div>${reject}</td>
      <td>${urgencyTag(o.urgency, o.urgency_label)}</td>
      <td>${statusTag(o.status, o.status_label)}</td>
      <td>${esc(o.reporter.real_name)}</td>
      <td>${o.repairer ? esc(o.repairer.real_name) : '<span class="subtle">—</span>'}</td>
      <td><div class="num">${fmtTime(o.created_at)}</div><div class="subtle">${fromNow(o.created_at)}</div></td>
      <td class="actions">${quick}<a class="btn btn-sm btn-ghost" href="order-detail.html?id=${o.id}">详情</a></td>
    </tr>`;
}

async function loadList() {
  syncUrl();
  $("#rows").innerHTML = skeletonRows(COLS);
  try {
    const data = await api.get("/api/orders", {
      page: state.page, size: state.size, status: state.status, keyword: state.keyword.trim(), urgency: state.urgency,
    });
    // 删除/筛选后当前页超出范围时，自动回到最后一页
    if (!data.items.length && data.total && state.page > 1) {
      state.page = Math.ceil(data.total / state.size);
      return loadList();
    }
    $("#rows").innerHTML = data.items.length
      ? data.items.map(row).join("")
      : `<tr><td colspan="${COLS}">${emptyState(state.keyword ? "没有找到匹配的工单" : "暂无工单", state.keyword ? "换个关键词试试" : "")}</td></tr>`;
    renderPager($("#pager"), data, (p) => { state.page = p; loadList(); });
  } catch (err) {
    $("#rows").innerHTML = `<tr><td colspan="${COLS}">${emptyState("加载失败", err.message, "alert")}</td></tr>`;
    showError(err);
  }
}

const refreshAll = () => Promise.all([loadCounts(), loadList()]).catch(showError);

$("#tabs").addEventListener("click", (e) => {
  const tab = e.target.closest(".tab");
  if (!tab) return;
  state.status = tab.dataset.status;
  state.page = 1;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
  loadList();
});
$("#keyword").addEventListener("input", debounce((e) => { state.keyword = e.target.value; state.page = 1; loadList(); }, 400));
$("#urgency").addEventListener("change", (e) => { state.urgency = e.target.value; state.page = 1; loadList(); });
$("#refreshBtn").addEventListener("click", refreshAll);
$("#rows").addEventListener("click", (e) => {
  const actionBtn = e.target.closest("[data-action]");
  const tr = e.target.closest("tr[data-id]");
  if (!tr) return;
  if (actionBtn) {
    e.stopPropagation();
    runAction(actionBtn.dataset.action, { id: Number(tr.dataset.id) }, refreshAll);
  } else if (!e.target.closest("a")) {
    location.href = `order-detail.html?id=${tr.dataset.id}`;
  }
});

refreshAll();
