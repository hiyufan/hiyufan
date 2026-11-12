// 用户管理：设备科管理员管理全部用户；部门管理员只能管理本部门普通员工（前后端双重限制）
import { renderPager } from "../components/pager.js";
import { api } from "../core/http.js";
import { icon } from "../core/icons.js";
import { mountLayout } from "../core/layout.js";
import { $, confirmDialog, debounce, emptyState, esc, fieldError, openModal, showError, skeletonRows, toast } from "../core/ui.js";

const me = await mountLayout({ active: "users", title: "用户管理" });
const isDeptAdmin = me.role === "DEPT_ADMIN";
const ROLE_TONE = { EMPLOYEE: "ug-LOW", DEPT_ADMIN: "st-ASSIGNED", DEVICE_ADMIN: "st-ARCHIVED", REPAIRER: "st-REPAIRING" };

const state = { keyword: "", role: "", dept_id: "", page: 1, size: 10 };
let roles = [];
let depts = [];
let skills = [];
let rows = [];

$("#pageDesc").textContent = isDeptAdmin ? `仅显示 ${me.dept_name} 的人员，可新增和管理本部门普通员工` : "管理全厂账号、角色与维修工擅长方向";
$("#searchBox").insertAdjacentHTML("afterbegin", icon("search"));
$("#addBtn").innerHTML = `${icon("plus", "icon-sm")}${isDeptAdmin ? "新增员工" : "新增用户"}`;
if (isDeptAdmin) $("#dept").classList.add("hidden");

const opt = (value, label, selected) => `<option value="${esc(value)}" ${selected ? "selected" : ""}>${esc(label)}</option>`;

async function loadOptions() {
  const [meta, d] = await Promise.all([api.get("/api/meta/options"), api.get("/api/depts")]);
  roles = meta.roles;
  skills = meta.fault_categories;
  depts = d;
  $("#role").insertAdjacentHTML("beforeend", roles.map((r) => opt(r.value, r.label)).join(""));
  $("#dept").insertAdjacentHTML("beforeend", depts.map((x) => opt(x.id, x.dept_name)).join(""));
}

const canManage = (u) => !isDeptAdmin || u.role === "EMPLOYEE";

async function load() {
  $("#rows").innerHTML = skeletonRows(8);
  try {
    const page = await api.get("/api/users", state);
    rows = page.items;
    $("#rows").innerHTML = rows.length ? rows.map((u) => `
      <tr data-id="${u.id}" style="${u.is_active ? "" : "opacity:.55"}">
        <td class="mono primary-text">${esc(u.username)}</td>
        <td><div style="display:flex;align-items:center;gap:8px"><span class="avatar" style="width:28px;height:28px;font-size:12px">${esc(u.real_name.slice(-2))}</span>${esc(u.real_name)}</div></td>
        <td><span class="tag plain ${ROLE_TONE[u.role]}">${esc(u.role_label)}</span></td>
        <td>${esc(u.dept_name)}<div class="subtle">${esc(u.factory_area)}</div></td>
        <td class="num">${esc(u.phone || "—")}</td>
        <td>${u.skills.length ? u.skills.map((s) => `<span class="chip" style="margin:1px">${esc(s)}</span>`).join("") : '<span class="subtle">—</span>'}</td>
        <td>${u.is_active ? '<span class="tag st-ARCHIVED">启用</span>' : '<span class="tag ug-LOW">停用</span>'}</td>
        <td class="actions">${canManage(u) && u.id !== me.id ? `
          <button class="btn btn-sm btn-ghost" data-act="edit">${icon("edit", "icon-sm")}编辑</button>
          <button class="btn btn-sm btn-ghost" data-act="reset">${icon("key", "icon-sm")}重置密码</button>
          <button class="btn btn-sm btn-ghost" data-act="toggle" style="color:${u.is_active ? "var(--danger)" : "var(--success)"}">${icon("power", "icon-sm")}${u.is_active ? "停用" : "启用"}</button>`
          : `<span class="subtle">${u.id === me.id ? "当前账号" : "无权管理"}</span>`}</td>
      </tr>`).join("") : `<tr><td colspan="8">${emptyState("没有符合条件的用户")}</td></tr>`;
    renderPager($("#pager"), page, (p) => { state.page = p; load(); });
  } catch (err) {
    showError(err);
  }
}

function userForm(u) {
  const roleChoices = isDeptAdmin ? roles.filter((r) => r.value === "EMPLOYEE") : roles;
  const deptChoices = isDeptAdmin ? depts.filter((d) => d.id === me.dept_id) : depts;
  const current = u?.role || "EMPLOYEE";
  return `
    <div class="form-row">
      <div class="field"><label>登录账号<span class="req">*</span></label>
        <input class="input mono" name="username" value="${esc(u?.username || "")}" ${u ? "disabled" : ""} placeholder="字母、数字、下划线" maxlength="30"></div>
      <div class="field"><label>姓名<span class="req">*</span></label>
        <input class="input" name="real_name" value="${esc(u?.real_name || "")}" maxlength="30"></div>
      <div class="field"><label>角色</label>
        <select class="input" name="role">${roleChoices.map((r) => opt(r.value, r.label, r.value === current)).join("")}</select></div>
      <div class="field"><label>所属部门</label>
        <select class="input" name="dept_id">${deptChoices.map((d) => opt(d.id, `${d.factory_area} · ${d.dept_name}`, d.id === (u?.dept_id ?? me.dept_id))).join("")}</select></div>
      <div class="field"><label>手机号</label>
        <input class="input num" name="phone" value="${esc(u?.phone || "")}" maxlength="11" inputmode="numeric"></div>
      ${u ? "" : '<div class="field"><label>初始密码</label><input class="input" value="123456" disabled><span class="hint">首次登录后请提醒用户修改</span></div>'}
    </div>
    <div class="field ${current === "REPAIRER" ? "" : "hidden"}" data-skills><label>擅长方向（智能派单依据）</label>
      <div class="preset-chips">${skills.map((s) => `
        <label class="chip-btn" style="display:inline-flex;align-items:center;gap:4px">
          <input type="checkbox" value="${esc(s)}" ${u?.skills.includes(s) ? "checked" : ""}>${esc(s)}</label>`).join("")}</div></div>`;
}

function openEditor(u) {
  openModal({
    title: u ? `编辑用户 · ${u.real_name}` : "新增用户",
    wide: true,
    confirmText: "保存",
    body: userForm(u),
    onOpen(el) {
      el.querySelector("[name=role]").addEventListener("change", (e) => {
        el.querySelector("[data-skills]").classList.toggle("hidden", e.target.value !== "REPAIRER");
      });
    },
    async onConfirm(el) {
      const get = (n) => el.querySelector(`[name=${n}]`);
      const data = {
        real_name: get("real_name").value.trim(),
        role: get("role").value,
        dept_id: Number(get("dept_id").value),
        phone: get("phone").value.trim() || null,
        skills: get("role").value === "REPAIRER" ? [...el.querySelectorAll("[data-skills] input:checked")].map((c) => c.value) : [],
      };
      let ok = true;
      if (!u && !/^[A-Za-z0-9_]{3,30}$/.test(get("username").value.trim())) { fieldError(get("username"), "3-30 位字母、数字或下划线"); ok = false; }
      if (data.real_name.length < 2) { fieldError(get("real_name"), "至少 2 个字"); ok = false; }
      if (data.phone && !/^1\d{10}$/.test(data.phone)) { fieldError(get("phone"), "请输入 11 位手机号"); ok = false; }
      if (!ok) throw new Error("请检查标红的字段");
      if (u) await api.put(`/api/users/${u.id}`, data);
      else await api.post("/api/users", { ...data, username: get("username").value.trim() });
      toast(u ? "用户已更新" : "用户已创建，初始密码 123456");
      load();
    },
  });
}

$("#addBtn").addEventListener("click", () => openEditor(null));
$("#rows").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-act]");
  if (!btn) return;
  const u = rows.find((x) => x.id === Number(btn.closest("tr").dataset.id));
  try {
    if (btn.dataset.act === "edit") return openEditor(u);
    if (btn.dataset.act === "reset") {
      if (!await confirmDialog({ title: "重置密码", message: `将「${u.real_name}」的密码重置为 123456？` })) return;
      await api.post(`/api/users/${u.id}/reset-password`);
      toast("密码已重置为 123456");
    }
    if (btn.dataset.act === "toggle") {
      const next = !u.is_active;
      if (!await confirmDialog({ title: next ? "启用账号" : "停用账号", message: next ? `启用「${u.real_name}」的账号？` : `停用后「${u.real_name}」将无法登录，确定吗？`, danger: !next, confirmText: next ? "启用" : "停用" })) return;
      await api.patch(`/api/users/${u.id}/status`, { is_active: next });
      toast(next ? "已启用" : "已停用");
      load();
    }
  } catch (err) { showError(err); }
});
["role", "dept"].forEach((id) => $(`#${id}`).addEventListener("change", (e) => {
  state[id === "dept" ? "dept_id" : id] = e.target.value;
  state.page = 1;
  load();
}));
$("#keyword").addEventListener("input", debounce((e) => { state.keyword = e.target.value.trim(); state.page = 1; load(); }, 400));

loadOptions().then(load).catch(showError);
