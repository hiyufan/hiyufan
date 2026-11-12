import { api } from "../core/http.js";
import { icon } from "../core/icons.js";
import { getToken, getUser, homeOf, saveSession } from "../core/session.js";
import { $, clearFieldErrors, esc, fieldError, toast, withLoading } from "../core/ui.js";

const DEMO = [
  ["emp01", "林志强", "普通员工", "报修"],
  ["dept01", "陈立华", "部门管理员", "部门看板"],
  ["sbk01", "王建国", "设备科管理员", "全厂看板 · 派单"],
  ["wx01", "张国庆", "维修工", "维修工作台"],
];
// 报修流程：顺序本身就是信息，所以用编号
const FLOW = [
  ["提交报修", "员工 · 附现场照片"],
  ["派单", "设备科 · 可驳回"],
  ["接单", "维修工"],
  ["完工提交", "维修工 · 填处理结果"],
  ["验收评价", "报修人 · 1-5 星"],
  ["归档", "进入维修知识库"],
];
const LEGEND = [
  ["var(--yellow)", "待派单", "警告：等待设备科处理"],
  ["var(--blue)", "待接单 / 维修中", "指令：维修工执行中"],
  ["var(--green)", "已归档", "安全：验收通过"],
  ["var(--red)", "已驳回", "禁止：需修改后重提"],
];
const NOTICE = {
  expired: ["warning", "登录已过期，请重新登录"],
  logout: ["success", "已退出登录"],
};

const params = new URLSearchParams(location.search);

// 已登录直接进入首页（登录状态保持）
if (getToken() && getUser() && !params.has("reason")) {
  location.replace(homeOf(getUser()));
}

$("#flow").innerHTML = FLOW.map(([t, d], i) => `<li><b>${i + 1}</b><div><span>${t}</span><small>${d}</small></div></li>`).join("");
$("#legend").innerHTML = LEGEND.map(([c, t, d]) => `<div><i class="sw" style="background:${c}"></i><span>${t}<br><small>${d}</small></span></div>`).join("");
$("#demoRows").innerHTML = DEMO.map(([u, n, r, h]) => `<tr data-user="${u}" tabindex="0"><td>${u}</td><td>${esc(n)}</td><td>${esc(r)}</td><td class="muted">${esc(h)}</td></tr>`).join("");

const reason = NOTICE[params.get("reason")];
if (reason) {
  $("#notice").innerHTML = `<div class="notice notice-${reason[0]}" style="margin-bottom:16px">${icon(reason[0] === "success" ? "checkCircle" : "alert", "icon-sm")}${reason[1]}</div>`;
}

const form = $("#loginForm");
const username = $("#username");
const password = $("#password");

$("#pwdToggle").addEventListener("click", (e) => {
  const show = password.type === "password";
  password.type = show ? "text" : "password";
  e.currentTarget.textContent = show ? "隐藏" : "显示";
});

function fillDemo(row) {
  username.value = row.dataset.user;
  password.value = "123456";
  clearFieldErrors(form);
  $("#loginBtn").focus();
}
$("#demoRows").addEventListener("click", (e) => { const row = e.target.closest("[data-user]"); if (row) fillDemo(row); });
$("#demoRows").addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.dataset.user) fillDemo(e.target); });

function validate() {
  clearFieldErrors(form);
  let ok = true;
  if (!username.value.trim()) { fieldError(username, "请输入账号"); ok = false; }
  if (password.value.length < 6) { fieldError(password, "密码至少 6 位"); ok = false; }
  return ok;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!validate()) return;
  await withLoading($("#loginBtn"), async () => {
    try {
      const data = await api.post("/api/auth/login", { username: username.value.trim(), password: password.value });
      saveSession(data.token, data.user);
      toast(`${data.user.real_name}，已登录`);
      const redirect = params.get("redirect");
      // 只允许跳转到本站页面，防止开放重定向
      const target = redirect && /^[\w-]+\.html(\?.*)?$/.test(redirect) && !redirect.startsWith("login") ? redirect : homeOf(data.user);
      setTimeout(() => location.replace(target), 300);
    } catch (err) {
      fieldError(password, err.message);
      password.select();
    }
  });
});
