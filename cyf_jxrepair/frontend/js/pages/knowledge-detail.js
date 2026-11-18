// 共享维修案例：展示归档知识，完整工单仍按原有角色与归属校验权限。
import { api } from "../core/http.js";
import { mountLayout } from "../core/layout.js";
import { $, emptyState, esc, fmtTime } from "../core/ui.js";

await mountLayout({ active: "knowledge", title: "维修案例" });

const id = Number(new URLSearchParams(location.search).get("id"));

async function load() {
  if (!Number.isInteger(id) || id < 1) {
    $("#caseDetail").innerHTML = emptyState("无法查看维修案例", "请选择一条已归档案例", "alert");
    return;
  }
  try {
    const c = await api.get(`/api/ai/knowledge/${id}`);
    document.title = `${c.order_no} · 维修案例 · CYF捷修云`;
    $("#caseDetail").innerHTML = `
      <div class="panel-head"><h2>${esc(c.device_name)}</h2><span class="mono subtle">${esc(c.order_no)}</span></div>
      <div class="panel-body">
        <p class="muted">${esc(c.category)} · ${fmtTime(c.archived_at, true).slice(0, 10)} 归档</p>
        <h3 style="margin-top:20px">故障现象</h3>
        <p style="white-space:pre-wrap;margin-top:8px">${esc(c.fault_desc)}</p>
        <h3 style="margin-top:20px">处理方法</h3>
        <p style="white-space:pre-wrap;margin-top:8px">${esc(c.repair_result)}</p>
      </div>`;
  } catch (err) {
    $("#caseDetail").innerHTML = emptyState("无法查看维修案例", err.message, "alert");
  }
}

load();
