// 员工报修页：新建报修 / 驳回后修改重提；输入故障描述时实时调用 AI 诊断与相似案例检索
import { createPhotoPicker } from "../components/photo-picker.js";
import { api, assetUrl } from "../core/http.js";
import { icon } from "../core/icons.js";
import { mountLayout } from "../core/layout.js";
import { $, clearFieldErrors, debounce, esc, fieldError, showError, toast, withLoading } from "../core/ui.js";

const resubmitId = Number(new URLSearchParams(location.search).get("resubmit")) || null;
const user = await mountLayout({
  active: resubmitId ? "orders" : "report",
  title: resubmitId ? "修改并重新提交" : "设备报修",
  roles: ["EMPLOYEE", "DEPT_ADMIN"],
});

const form = $("#reportForm");
const deviceSelect = $("#deviceId");
const faultDesc = $("#faultDesc");
let devices = [];
let picker;
let original = null; // 驳回重提时的原工单

// ------------------------------------------------------------ 设备下拉：按厂区分组，本部门设备排在最前
function renderDevices(selectedId) {
  const groups = new Map();
  devices.forEach((d) => {
    const key = d.dept_id === user.dept_id ? `★ 本部门 · ${d.dept_name}` : `${d.factory_area} · ${d.dept_name}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(d);
  });
  const ordered = [...groups.entries()].sort(([a], [b]) => (a.startsWith("★") ? -1 : b.startsWith("★") ? 1 : a.localeCompare(b)));
  deviceSelect.innerHTML = '<option value="">请选择报修设备</option>' + ordered.map(([label, list]) => `
    <optgroup label="${esc(label)}">${list.map((d) => `
      <option value="${d.id}" ${d.id === selectedId ? "selected" : ""}>${esc(d.device_name)}（${esc(d.device_code)}）${d.status === "REPAIRING" ? " · 维修中" : ""}</option>`).join("")}
    </optgroup>`).join("");
  showDeviceHint();
}

function showDeviceHint() {
  const d = devices.find((x) => x.id === Number(deviceSelect.value));
  $("#deviceHint").innerHTML = d
    ? `<span>${esc(d.factory_area)} · ${esc(d.location)}</span><span class="chip">${esc(d.category)}</span>${d.model ? `<span class="mono subtle">${esc(d.model)}</span>` : ""}`
    : "";
}

// ------------------------------------------------------------ 故障初判与相似案例
function renderAiEmpty() {
  $("#aiEngine").textContent = "";
  $("#aiBody").innerHTML = '<p class="side-empty">输入故障描述后，这里会给出可能原因和处理建议，供你和设备科参考。</p>';
  $("#similarBody").innerHTML = '<p class="side-empty">同类故障以前怎么修好的，会列在这里。</p>';
}

/** 置信度来源：规则命中了哪些关键词、哪些历史案例支持这个判断 */
function evidence(it) {
  const parts = [];
  if (it.matched_keywords.length) parts.push(`规则 ${Math.round(it.rule_confidence * 100)}%：命中「${it.matched_keywords.map(esc).join("」「")}」`);
  if (it.evidence_cases.length) {
    parts.push(`案例 ${Math.round(it.case_confidence * 100)}%：${it.evidence_cases.map((c) =>
      `<a href="order-detail.html?id=${c.order_id}" target="_blank" rel="noopener">${esc(c.order_no)}</a>`).join("、")}`);
  }
  return parts.join("<br>");
}

function renderDiagnosis(d) {
  $("#aiEngine").textContent = d.engine === "llm" ? "大模型" : "本地故障知识库";
  const items = d.items.length ? d.items.map((it) => `
    <div class="diag">
      <div class="diag-top"><b>${esc(it.category)}</b><span class="meter"><i style="width:${Math.round(it.confidence * 100)}%"></i></span>
        <span class="subtle num">${Math.round(it.confidence * 100)}%</span></div>
      <p><em>可能原因</em>　${esc(it.cause)}</p>
      <p><em>建议</em>　${esc(it.suggestion)}</p>
      <p class="evidence">${evidence(it)}</p>
    </div>`).join("") : '<p class="side-empty">没有匹配到已知故障，请补充更具体的现象。</p>';
  $("#aiBody").innerHTML = `
    <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px">
      <span class="subtle">安全风险</span><span class="risk risk-${esc(d.risk_level)}">${esc(d.risk_level)}</span></div>
    ${d.risk_tips.map((t) => `<div class="notice notice-${d.risk_level === "高" ? "danger" : "warning"}" style="margin-bottom:10px">${icon("alert", "icon-sm")}<span>${esc(t)}</span></div>`).join("")}
    ${items}`;
  // 识别到高风险时自动把紧急程度调为"紧急"（用户仍可手动修改）
  if (d.risk_level === "高") form.querySelector('input[value="HIGH"]').checked = true;
}

function renderSimilar(hits) {
  $("#similarBody").innerHTML = hits.length ? hits.map((h) => `
    <a class="case" href="order-detail.html?id=${h.order_id}" target="_blank" rel="noopener">
      <b>${esc(h.device_name)}：${esc(h.fault_desc)}</b>
      <span>处理：${esc(h.repair_result)}</span></a>`).join("") : '<p class="side-empty">知识库里还没有相似案例。</p>';
}

const analyze = debounce(async () => {
  const text = faultDesc.value.trim();
  if (text.length < 4) return renderAiEmpty();
  try {
    const [diag, hits] = await Promise.all([
      api.post("/api/ai/diagnose", { fault_desc: text, device_id: Number(deviceSelect.value) || null }),
      api.get("/api/ai/knowledge", { q: text, top_k: 3 }),
    ]);
    renderDiagnosis(diag);
    renderSimilar(hits);
  } catch (err) {
    $("#aiBody").innerHTML = `<p class="side-empty">暂时无法初判：${esc(err.message)}</p>`;
  }
}, 500);

// ------------------------------------------------------------ 表单
function validate() {
  clearFieldErrors(form);
  let ok = true;
  if (!deviceSelect.value) { fieldError(deviceSelect, "请选择报修设备"); ok = false; }
  if (faultDesc.value.trim().length < 5) { fieldError(faultDesc, "故障描述至少 5 个字"); ok = false; }
  if (!ok) form.querySelector(".field.invalid .input")?.focus();
  return ok;
}

function buildForm() {
  const data = new FormData();
  data.append("device_id", deviceSelect.value);
  data.append("fault_desc", faultDesc.value.trim());
  data.append("urgency", form.querySelector("input[name=urgency]:checked").value);
  picker.getFiles().forEach((f) => data.append("photos", f));
  if (resubmitId) data.append("keep_photos", String(picker.keepsOriginal()));
  return data;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!validate()) return;
  await withLoading($("#submitBtn"), async () => {
    try {
      const url = resubmitId ? `/api/orders/${resubmitId}/resubmit` : "/api/orders";
      const order = await api.upload(url, buildForm());
      toast(resubmitId ? "已重新提交，等待设备科派单" : `报修成功，工单号 ${order.order_no}`);
      setTimeout(() => { location.href = `order-detail.html?id=${order.id}`; }, 700);
    } catch (err) {
      showError(err);
    }
  });
});

$("#resetBtn").addEventListener("click", () => {
  form.reset();
  clearFieldErrors(form);
  picker.reset();
  if (original) fillOriginal();
  $("#descCount").textContent = faultDesc.value.length;
  showDeviceHint();
  renderAiEmpty();
});

faultDesc.addEventListener("input", () => {
  $("#descCount").textContent = faultDesc.value.length;
  analyze();
});
deviceSelect.addEventListener("change", () => { showDeviceHint(); analyze(); });

// ------------------------------------------------------------ 驳回重提：回填原工单
function fillOriginal() {
  deviceSelect.value = original.device.id;
  faultDesc.value = original.fault_desc;
  form.querySelector(`input[name=urgency][value=${original.urgency}]`).checked = true;
}

async function init() {
  const [opts, meta] = await Promise.all([api.get("/api/devices/options"), api.get("/api/meta/options")]);
  devices = opts;
  const upload = meta.upload;

  if (resubmitId) {
    original = await api.get(`/api/orders/${resubmitId}`);
    if (!original.actions.some((a) => a.value === "RESUBMIT")) {
      toast("该工单当前不能修改重提", "warning");
      setTimeout(() => { location.replace(`order-detail.html?id=${resubmitId}`); }, 800);
      return;
    }
    $("#pageTitle").textContent = `修改并重新提交 · ${original.order_no}`;
    $("#pageDesc").textContent = "根据驳回意见修改后重新提交，工单将回到「待派单」状态。";
    $("#rejectBanner").innerHTML = `<div class="notice notice-danger" style="margin-bottom:16px">${icon("xCircle", "icon-sm")}
      <span><b>驳回意见：</b>${esc(original.reject_reason || "无")}</span></div>`;
    $("#submitBtn").textContent = "重新提交";
  }

  renderDevices(original?.device.id);
  picker = createPhotoPicker($("#photoPicker"), {
    maxCount: upload.max_count, maxMb: upload.max_mb,
    existing: (original?.photo_urls || []).map(assetUrl),
  });
  if (original) {
    fillOriginal();
    $("#descCount").textContent = faultDesc.value.length;
    showDeviceHint();
    analyze();
  } else {
    renderAiEmpty();
  }
}

init().catch(showError);
