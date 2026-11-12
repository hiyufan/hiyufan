// 工单卡片：派单中心与维修工作台共用
import { icon } from "../core/icons.js";
import { esc, fromNow, statusTag, urgencyTag } from "../core/ui.js";

/**
 * @param {object} o 工单（OrderBrief）
 * @param {{actions: {value:string,label:string}[], summary?: object}} extra
 */
export function orderCard(o, { actions = [], summary } = {}) {
  const chips = summary
    ? `<div class="kv"><span class="chip">${esc(summary.fields["故障类型"])}</span>
         <span class="risk-chip risk-${esc(summary.fields["风险等级"])}">风险 ${esc(summary.fields["风险等级"])}</span></div>`
    : "";
  const buttons = actions.map((a) => `
    <button type="button" class="btn btn-sm ${a.value === "REJECT" ? "btn-danger" : "btn-primary"}" data-action="${a.value}">${esc(a.label)}</button>`).join("");
  return `
    <article class="work-card ${o.urgency === "HIGH" ? "urgent" : ""}" data-id="${o.id}">
      <div class="wc-head">
        <span class="mono">${esc(o.order_no)}</span>
        ${o.is_overdue ? '<span class="tag tag-overdue">超期</span>' : ""}
        ${urgencyTag(o.urgency, o.urgency_label)}${statusTag(o.status, o.status_label)}
      </div>
      <div>
        <h4>${esc(o.device.device_name)} <span class="subtle mono">${esc(o.device.device_code)}</span></h4>
        <div class="loc">${icon("mapPin", "icon-sm")}${esc(o.device.factory_area)} · ${esc(o.device.location)}</div>
      </div>
      <p class="fault" title="${esc(o.fault_desc)}">${esc(o.fault_desc)}</p>
      ${chips}
      <div class="wc-foot">
        <span class="subtle">${esc(o.reporter.real_name)} · ${fromNow(o.created_at)}${o.repairer ? ` · 维修：${esc(o.repairer.real_name)}` : ""}</span>
        <a class="btn btn-sm btn-ghost" href="order-detail.html?id=${o.id}">详情</a>
        ${buttons}
      </div>
    </article>`;
}
