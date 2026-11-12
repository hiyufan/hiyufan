// 设备台账：分页 + 多条件筛选 + 新增/编辑/删除
import { renderPager } from "../components/pager.js";
import { api } from "../core/http.js";
import { icon } from "../core/icons.js";
import { mountLayout } from "../core/layout.js";
import { $, confirmDialog, debounce, emptyState, esc, fieldError, openModal, showError, skeletonRows, toast } from "../core/ui.js";

await mountLayout({ active: "devices", title: "设备台账" });

const DEVICE_TONE = { NORMAL: "st-ARCHIVED", REPAIRING: "st-REPAIRING", SCRAPPED: "st-REJECTED" };
const state = { keyword: "", category: "", dept_id: "", status: "", page: 1, size: 10 };
let depts = [];
let categories = [];
let statusOptions = [];
let rows = [];

$("#searchBox").insertAdjacentHTML("afterbegin", icon("search"));
$("#addBtn").innerHTML = `${icon("plus", "icon-sm")}新增设备`;

const opt = (value, label, selected) => `<option value="${esc(value)}" ${selected ? "selected" : ""}>${esc(label)}</option>`;

async function loadOptions() {
  const [d, c, meta] = await Promise.all([api.get("/api/depts"), api.get("/api/devices/categories"), api.get("/api/meta/options")]);
  depts = d;
  categories = c;
  statusOptions = meta.device_status;
  $("#category").insertAdjacentHTML("beforeend", categories.map((x) => opt(x, x)).join(""));
  $("#dept").insertAdjacentHTML("beforeend", depts.map((x) => opt(x.id, `${x.factory_area} · ${x.dept_name}`)).join(""));
  $("#status").insertAdjacentHTML("beforeend", statusOptions.map((x) => opt(x.value, x.label)).join(""));
}

async function load() {
  $("#rows").innerHTML = skeletonRows(9);
  try {
    const page = await api.get("/api/devices", state);
    rows = page.items;
    $("#rows").innerHTML = rows.length ? rows.map((d) => `
      <tr data-id="${d.id}">
        <td class="mono primary-text">${esc(d.device_code)}</td>
        <td class="primary-text">${esc(d.device_name)}</td>
        <td><span class="chip">${esc(d.category)}</span></td>
        <td class="muted">${esc(d.model || "—")}</td>
        <td>${esc(d.dept_name)}<div class="subtle">${esc(d.factory_area)}</div></td>
        <td>${esc(d.location)}</td>
        <td><span class="tag ${DEVICE_TONE[d.status]}">${esc(d.status_label)}</span></td>
        <td class="num">${d.fault_count ? `<a href="orders.html?keyword=${encodeURIComponent(d.device_code)}">${d.fault_count} 次</a>` : '<span class="subtle">0</span>'}</td>
        <td class="actions">
          <button class="btn btn-sm btn-ghost" data-edit>${icon("edit", "icon-sm")}编辑</button>
          <button class="btn btn-sm btn-ghost" data-del style="color:var(--danger)">${icon("trash", "icon-sm")}删除</button>
        </td>
      </tr>`).join("") : `<tr><td colspan="9">${emptyState("没有符合条件的设备")}</td></tr>`;
    renderPager($("#pager"), page, (p) => { state.page = p; load(); });
  } catch (err) {
    showError(err);
  }
}

function deviceForm(d = {}) {
  return `
    <div class="form-row">
      <div class="field"><label>设备编号<span class="req">*</span></label>
        <input class="input mono" name="device_code" value="${esc(d.device_code || "")}" placeholder="如 CNC-A-003" maxlength="30"></div>
      <div class="field"><label>设备名称<span class="req">*</span></label>
        <input class="input" name="device_name" value="${esc(d.device_name || "")}" maxlength="50"></div>
      <div class="field"><label>设备类别<span class="req">*</span></label>
        <input class="input" name="category" list="categoryList" value="${esc(d.category || "")}" maxlength="20" placeholder="可选择或输入新类别">
        <datalist id="categoryList">${categories.map((c) => `<option value="${esc(c)}">`).join("")}</datalist></div>
      <div class="field"><label>规格型号</label>
        <input class="input" name="model" value="${esc(d.model || "")}" maxlength="50"></div>
      <div class="field"><label>使用部门<span class="req">*</span></label>
        <select class="input" name="dept_id">${depts.map((x) => opt(x.id, `${x.factory_area} · ${x.dept_name}`, x.id === d.dept_id)).join("")}</select></div>
      <div class="field"><label>安装位置<span class="req">*</span></label>
        <input class="input" name="location" value="${esc(d.location || "")}" maxlength="50" placeholder="如 A厂区1号线"></div>
      <div class="field"><label>设备状态</label>
        <select class="input" name="status">${statusOptions.map((x) => opt(x.value, x.label, x.value === (d.status || "NORMAL"))).join("")}</select></div>
      <div class="field"><label>购置日期</label>
        <input class="input" type="date" name="purchase_date" value="${esc(d.purchase_date || "")}"></div>
    </div>`;
}

function collect(el) {
  const get = (n) => el.querySelector(`[name=${n}]`);
  const data = {
    device_code: get("device_code").value.trim(), device_name: get("device_name").value.trim(),
    category: get("category").value.trim(), model: get("model").value.trim() || null,
    dept_id: Number(get("dept_id").value), location: get("location").value.trim(),
    status: get("status").value, purchase_date: get("purchase_date").value || null,
  };
  const rules = [
    ["device_code", /^[A-Za-z0-9-]{3,30}$/.test(data.device_code), "3-30 位字母、数字或短横线"],
    ["device_name", data.device_name.length >= 2, "至少 2 个字"],
    ["category", data.category.length >= 2, "请填写设备类别"],
    ["location", data.location.length >= 2, "请填写安装位置"],
  ];
  let ok = true;
  rules.forEach(([name, pass, msg]) => { fieldError(get(name), pass ? "" : msg); ok &&= pass; });
  if (!ok) throw new Error("请检查标红的字段");
  return data;
}

function openEditor(device) {
  openModal({
    title: device ? `编辑设备 · ${device.device_code}` : "新增设备",
    wide: true,
    confirmText: "保存",
    body: deviceForm(device),
    async onConfirm(el) {
      const data = collect(el);
      if (device) await api.put(`/api/devices/${device.id}`, data);
      else await api.post("/api/devices", data);
      toast(device ? "设备已更新" : "设备已新增");
      load();
    },
  });
}

$("#addBtn").addEventListener("click", () => openEditor(null));
$("#rows").addEventListener("click", async (e) => {
  const tr = e.target.closest("tr[data-id]");
  if (!tr) return;
  const device = rows.find((d) => d.id === Number(tr.dataset.id));
  if (e.target.closest("[data-edit]")) openEditor(device);
  if (e.target.closest("[data-del]")) {
    const ok = await confirmDialog({ title: "删除设备", message: `确定删除「${device.device_name}（${device.device_code}）」吗？有报修记录的设备不能删除。`, confirmText: "删除", danger: true });
    if (!ok) return;
    try {
      await api.del(`/api/devices/${device.id}`);
      toast("设备已删除");
      load();
    } catch (err) { showError(err); }
  }
});
["category", "dept", "status"].forEach((id) => $(`#${id}`).addEventListener("change", (e) => {
  state[id === "dept" ? "dept_id" : id] = e.target.value;
  state.page = 1;
  load();
}));
$("#keyword").addEventListener("input", debounce((e) => { state.keyword = e.target.value.trim(); state.page = 1; load(); }, 400));

loadOptions().then(load).catch(showError);
