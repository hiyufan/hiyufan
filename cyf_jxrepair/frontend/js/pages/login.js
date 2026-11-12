import { api } from "../core/http.js";
import { icon } from "../core/icons.js";
import { getToken, getUser, homeOf, saveSession } from "../core/session.js";
import { $, clearFieldErrors, esc, fieldError, toast, withLoading } from "../core/ui.js";

const DEMO = [
  { username: "emp01", name: "林志强", role: "普通员工" },
  { username: "dept01", name: "陈立华", role: "部门管理员" },
  { username: "sbk01", name: "王建国", role: "设备科管理员" },
  { username: "wx01", name: "张国庆", role: "维修工" },
];
const FLOW = ["提交报修", "设备科派单", "维修工接单", "完工提交", "验收评价", "工单归档"];
const NOTICE = {
  expired: ["warning", "登录已过期，请重新登录"],
  logout: ["success", "已安全退出"],
};

const params = new URLSearchParams(location.search);

// 已登录直接进入首页（登录状态保持）
if (getToken() && getUser() && !params.has("reason")) {
  location.replace(homeOf(getUser()));
}

$("#heroFlow").innerHTML = FLOW.map((s, i) => `<span>${i ? icon("arrowRight") : icon("checkCircle")}${s}</span>`).join("");
$("#userIcon").insertAdjacentHTML("afterbegin", icon("user"));
$("#pwdIcon").insertAdjacentHTML("afterbegin", icon("lock"));
$("#pwdToggle").innerHTML = icon("eye", "icon-sm");
$("#demoGrid").innerHTML = DEMO.map((d) => `
  <button type="button" data-user="${d.username}"><b>${esc(d.role)}</b><span>${d.username} · ${esc(d.name)}</span></button>`).join("");

const reason = NOTICE[params.get("reason")];
if (reason) {
  $("#notice").innerHTML = `<div class="alert alert-${reason[0]} login-notice">${icon(reason[0] === "success" ? "checkCircle" : "alert", "icon-sm")}${reason[1]}</div>`;
}

const form = $("#loginForm");
const username = $("#username");
const password = $("#password");

$("#pwdToggle").addEventListener("click", () => {
  password.type = password.type === "password" ? "text" : "password";
});

$("#demoGrid").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-user]");
  if (!btn) return;
  username.value = btn.dataset.user;
  password.value = "123456";
  clearFieldErrors(form);
  $("#loginBtn").focus();
});

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
      toast(`欢迎回来，${data.user.real_name}`);
      const redirect = params.get("redirect");
      // 只允许跳转到本站页面，防止开放重定向
      const target = redirect && /^[\w-]+\.html(\?.*)?$/.test(redirect) && !redirect.startsWith("login") ? redirect : homeOf(data.user);
      setTimeout(() => location.replace(target), 400);
    } catch (err) {
      fieldError(password, err.message);
      password.select();
    }
  });
});
