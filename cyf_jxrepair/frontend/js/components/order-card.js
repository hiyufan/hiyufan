// 工单行（T 卡式）：派单页与维修工作台共用。
// 四列：工单号与状态 | 设备与故障 | 初判（故障类型、风险）| 操作
import { esc, fromNow, statusTag, urgencyTag } from "../core/ui.js";

/**
 * @param {object} o 工单（OrderBrief）
 * @param {{actions?: {value:string,label:string}[], summary?: object}} extra
 */
export function orderCard(o, { actions = [], summary } = {}) {
  const judge = summary
    ? `<span>${esc(summary.fields["故障类型"])}</span><span class="risk risk-${esc(summary.fields["风险等级"])}">风险${esc(summary.fields["风险等级"])}</span>`
    : `<span class="subtle">${esc(o.reporter.real_name)} 报修${o.repairer ? ` · ${esc(o.repairer.real_name)} 维修` : ""}</span>`;
  const buttons = actions.map((a) => `
    <button type="button" class="btn btn-sm ${a.value === "REJECT" ? "btn-danger" : "btn-primary"}" data-action="${a.value}">${esc(a.label)}</button>`).join("");
  return `
    <article class="ticket" data-id="${o.id}">
      <div>
        <a class="no" href="order-detail.html?id=${o.id}">${esc(o.order_no)}</a>
        <div class="meta">${statusTag(o.status, o.status_label)}${urgencyTag(o.urgency, o.urgency_label)}
          ${o.is_overdue ? '<span class="flag-overdue">超期 48h+</span>' : ""}</div>
      </div>
      <div style="min-width:0">
        <h4>${esc(o.device.device_name)}<span class="mono">${esc(o.device.device_code)}</span></h4>
        <p class="fault">${esc(o.fault_desc)}</p>
        <div class="where">${esc(o.device.factory_area)} · ${esc(o.device.location)} · ${fromNow(o.created_at)}提交</div>
      </div>
      <div class="judge">${judge}</div>
      <div class="acts"><a class="btn btn-sm btn-ghost" href="order-detail.html?id=${o.id}">详情</a>${buttons}</div>
    </article>`;
}
