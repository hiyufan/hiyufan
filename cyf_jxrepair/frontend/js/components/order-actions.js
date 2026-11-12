// 工单操作弹窗：派单 / 驳回 / 接单 / 完工 / 验收评价 / 验收不通过
// 可执行哪些操作由后端 detail.actions 决定，前端只负责收集参数并调用接口
import { api } from "../core/http.js";
import { icon } from "../core/icons.js";
import { $, $$, esc, fieldError, openModal, toast } from "../core/ui.js";

// 驳回常用意见，点击即可填入（减少设备科重复打字）
const REJECT_PRESETS = ["故障描述不清，请补充具体现象", "请上传现场照片", "报修设备选择错误，请核对设备编号", "该故障已有工单在处理，请勿重复报修"];
const FAIL_PRESETS = ["试机后故障复现", "问题未彻底解决", "现场未清理"];
const SCORE_TEXT = ["", "非常不满意", "不满意", "一般", "满意", "非常满意"];

function requireText(el, min, label) {
  const value = el.value.trim();
  if (value.length < min) {
    fieldError(el, `${label}至少 ${min} 个字`);
    el.focus();
    throw new Error(`请填写${label}`);
  }
  fieldError(el, "");
  return value;
}

function presetChips(presets, target) {
  return `<div class="preset-chips" data-target="${target}">${presets.map((p) => `<button type="button" class="chip-btn">${esc(p)}</button>`).join("")}</div>`;
}

function bindPresets(el) {
  $$(".preset-chips", el).forEach((box) => {
    const input = $(`[name=${box.dataset.target}]`, el);
    box.addEventListener("click", (e) => {
      const chip = e.target.closest(".chip-btn");
      if (!chip) return;
      input.value = input.value ? `${input.value}；${chip.textContent}` : chip.textContent;
      input.focus();
    });
  });
}

// ------------------------------------------------------------ 派单：先初判故障类型，再按擅长方向与负载推荐维修工
function repairerRow(r, checked) {
  return `
    <label class="pick">
      <input type="radio" name="repairer" value="${r.id}" ${checked ? "checked" : ""}>
      <b data-name>${esc(r.real_name)}</b>
      <span class="skills">${r.skills.map(esc).join("、") || "通用"}${r.matched ? '<span class="match">擅长</span>' : ""}</span>
      <span class="load">${r.active_orders}<small>单在手</small></span>
    </label>`;
}

async function openDispatch(order, onSuccess) {
  const { el } = openModal({
    title: `派单 ${order.order_no}`,
    confirmText: "派单",
    wide: true,
    body: `
      <div class="brief">
        <b>${esc(order.device.device_name)}</b> <span class="mono subtle">${esc(order.device.device_code)}</span>
        <span class="subtle"> · ${esc(order.device.factory_area)} ${esc(order.device.location)}</span>
        <p>${esc(order.fault_desc)}</p>
      </div>
      <div class="judge-box" data-ai><div class="skeleton" style="width:60%"></div></div>
      <div class="field"><span class="field-label">维修工<span class="req">*</span></span>
        <div class="picks" data-repairers><div class="panel-body"><div class="skeleton"></div></div></div>
        <span class="hint">擅长方向与本次故障类型一致的排在前面，同组内按手头工单从少到多</span></div>
      <div class="field"><label for="dispatchRemark">派单备注</label>
        <input class="input" id="dispatchRemark" name="remark" maxlength="200" placeholder="选填，如：先断电挂牌再拆检"></div>`,
    async onConfirm(modal) {
      const picked = $("input[name=repairer]:checked", modal);
      if (!picked) throw new Error("请选择一名维修工");
      await api.post(`/api/orders/${order.id}/dispatch`, {
        repairer_id: Number(picked.value),
        remark: $("[name=remark]", modal).value.trim() || null,
      });
      toast(`已派给 ${picked.closest(".pick").querySelector("[data-name]").textContent}`);
      onSuccess?.();
    },
  });

  let category;
  try {
    const diag = await api.post("/api/ai/diagnose", { fault_desc: order.fault_desc, device_id: order.device.id });
    const top = diag.items[0];
    category = top?.category;
    $("[data-ai]", el).innerHTML = top
      ? `<b>初判：${esc(top.category)}</b> <span class="subtle">匹配度 ${Math.round(top.confidence * 100)}%</span>
         <p>可能原因：${esc(top.cause)}</p><p class="muted">建议：${esc(top.suggestion)}</p>
         ${diag.risk_tips.map((t) => `<p style="color:var(--red)">${esc(t)}</p>`).join("")}`
      : "<b>未能初判</b><p class=\"muted\">知识库没有匹配的故障，请按经验指派。</p>";
  } catch (err) {
    $("[data-ai]", el).innerHTML = `<p class="muted">暂时无法初判：${esc(err.message)}</p>`;
  }
  try {
    const repairers = await api.get("/api/repairers", { category });
    $("[data-repairers]", el).innerHTML = repairers.length
      ? repairers.map((r, i) => repairerRow(r, i === 0)).join("")
      : '<div class="panel-body muted">没有在岗的维修工</div>';
  } catch (err) {
    $("[data-repairers]", el).innerHTML = `<div class="panel-body muted">${esc(err.message)}</div>`;
  }
}

// ------------------------------------------------------------ 其余操作
function openReject(order, onSuccess) {
  openModal({
    title: `驳回工单 · ${order.order_no}`,
    confirmText: "确认驳回",
    danger: true,
    body: `
      <p class="modal-intro">驳回后报修人可在「我的报修」中查看原因，修改后重新提交。</p>
      <div class="field"><label>驳回意见<span class="req">*</span></label>
        <textarea class="input" name="reason" maxlength="200" placeholder="请写明驳回原因，便于报修人修改"></textarea>
        ${presetChips(REJECT_PRESETS, "reason")}</div>`,
    onOpen: bindPresets,
    async onConfirm(el) {
      const reason = requireText($("[name=reason]", el), 2, "驳回意见");
      await api.post(`/api/orders/${order.id}/reject`, { reason });
      toast("已驳回，报修人将看到驳回意见");
      onSuccess?.();
    },
  });
}

function openTake(order, onSuccess) {
  openModal({
    title: `接单 · ${order.order_no}`,
    confirmText: "确认接单",
    body: `
      <p class="modal-intro">接单后工单进入「维修中」，设备状态同步标记为维修中。</p>
      <div class="field"><label>接单备注</label>
        <input class="input" name="remark" maxlength="200" placeholder="选填，如：预计 30 分钟到场"></div>`,
    async onConfirm(el) {
      await api.post(`/api/orders/${order.id}/take`, { remark: $("[name=remark]", el).value.trim() || null });
      toast("接单成功，请尽快到场处理");
      onSuccess?.();
    },
  });
}

function openComplete(order, onSuccess) {
  openModal({
    title: `完工提交 · ${order.order_no}`,
    confirmText: "提交完工",
    body: `
      <div class="field"><label>处理结果<span class="req">*</span></label>
        <textarea class="input" name="result" maxlength="500" placeholder="故障原因、更换的配件、试机情况等，将沉淀进维修知识库"></textarea>
        <span class="hint">写得越具体，后续相似故障检索越准确</span></div>`,
    async onConfirm(el) {
      const result = requireText($("[name=result]", el), 5, "处理结果");
      await api.post(`/api/orders/${order.id}/complete`, { repair_result: result });
      toast("已提交完工，等待报修人验收");
      onSuccess?.();
    },
  });
}

function openEvaluate(order, onSuccess) {
  let score = 5;
  openModal({
    title: `验收评价 · ${order.order_no}`,
    confirmText: "验收通过并归档",
    body: `
      ${order.repair_result ? `<div class="notice notice-info"><span><b>维修结果</b>　${esc(order.repair_result)}</span></div>` : ""}
      <div class="field" style="margin-top:14px"><label>满意度评分</label>
        <div class="rate-row"><div class="stars" role="radiogroup">
          ${[1, 2, 3, 4, 5].map((n) => `<button type="button" data-score="${n}" class="on" aria-label="${n} 星">${icon("star")}</button>`).join("")}
        </div><span class="rate-text">${SCORE_TEXT[5]}</span></div></div>
      <div class="field"><label>评价内容</label>
        <textarea class="input" name="comment" maxlength="300" placeholder="选填，说说维修速度、质量、服务态度"></textarea></div>`,
    onOpen(el) {
      const paint = (n) => {
        $$(".stars button", el).forEach((b) => b.classList.toggle("on", Number(b.dataset.score) <= n));
        $(".rate-text", el).textContent = SCORE_TEXT[n];
      };
      $(".stars", el).addEventListener("click", (e) => {
        const btn = e.target.closest("[data-score]");
        if (btn) { score = Number(btn.dataset.score); paint(score); }
      });
      $(".stars", el).addEventListener("mouseover", (e) => {
        const btn = e.target.closest("[data-score]");
        if (btn) paint(Number(btn.dataset.score));
      });
      $(".stars", el).addEventListener("mouseleave", () => paint(score));
    },
    async onConfirm(el) {
      await api.post(`/api/orders/${order.id}/evaluate`, { score, comment: $("[name=comment]", el).value.trim() || null });
      toast("验收完成，工单已归档");
      onSuccess?.();
    },
  });
}

function openAcceptFail(order, onSuccess) {
  openModal({
    title: `验收不通过 · ${order.order_no}`,
    confirmText: "退回返修",
    danger: true,
    body: `
      <p class="modal-intro">工单将退回「维修中」，由原维修工继续处理。</p>
      <div class="field"><label>不通过原因<span class="req">*</span></label>
        <textarea class="input" name="reason" maxlength="200"></textarea>${presetChips(FAIL_PRESETS, "reason")}</div>`,
    onOpen: bindPresets,
    async onConfirm(el) {
      const reason = requireText($("[name=reason]", el), 2, "不通过原因");
      await api.post(`/api/orders/${order.id}/accept-fail`, { reason });
      toast("已退回维修工返修", "warning");
      onSuccess?.();
    },
  });
}

const HANDLERS = {
  DISPATCH: openDispatch,
  REJECT: openReject,
  TAKE: openTake,
  COMPLETE: openComplete,
  ACCEPT: openEvaluate,
  ACCEPT_FAIL: openAcceptFail,
  RESUBMIT: (order) => { location.href = `report.html?resubmit=${order.id}`; },
};

/** 按钮样式：主操作用主色，否定类操作用危险色 */
export const ACTION_STYLE = {
  DISPATCH: "btn-primary", TAKE: "btn-primary", COMPLETE: "btn-primary", ACCEPT: "btn-primary",
  RESUBMIT: "btn-primary", REJECT: "btn-danger", ACCEPT_FAIL: "btn-danger",
};
export function actionButtons(actions, size = "") {
  return actions.map((a) => `<button type="button" class="btn ${size} ${ACTION_STYLE[a.value] || ""}" data-action="${a.value}">
    ${esc(a.label)}</button>`).join("");
}

/**
 * 执行操作：打开对应弹窗，接口调用成功后执行 onSuccess（通常用于刷新页面数据）。
 * 用户取消时不会触发 onSuccess。
 */
export function runAction(action, order, onSuccess) {
  HANDLERS[action]?.(order, onSuccess);
}
