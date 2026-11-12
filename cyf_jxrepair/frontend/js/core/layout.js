// 页面框架：顶部导航（系统标识 · 按角色生成的菜单 · 当前用户）；同时负责页面级的登录与角色守卫
import { api } from "./http.js";
import { icon } from "./icons.js";
import { clearSession, getToken, getUser, homeOf, saveSession, toLogin } from "./session.js";
import { $, esc, openModal, toast } from "./ui.js";

const ALL = ["EMPLOYEE", "DEPT_ADMIN", "DEVICE_ADMIN", "REPAIRER"];

/** 菜单配置：roles 决定谁能看到；页面守卫也复用这份配置。badge 为菜单上显示数量的工单状态 */
export const MENU = [
  { key: "dashboard", href: "dashboard.html", text: "统计看板", roles: ["DEVICE_ADMIN", "DEPT_ADMIN"] },
  { key: "dispatch", href: "dispatch.html", text: "派单", roles: ["DEVICE_ADMIN"], badge: "PENDING" },
  { key: "workbench", href: "workbench.html", text: "维修工作台", roles: ["REPAIRER"], badge: "ASSIGNED" },
  { key: "report", href: "report.html", text: "报修", roles: ["EMPLOYEE", "DEPT_ADMIN"] },
  { key: "orders", href: "orders.html", text: "工单", roles: ALL },
  { key: "knowledge", href: "knowledge.html", text: "维修知识库", roles: ALL },
  { key: "devices", href: "devices.html", text: "设备台账", roles: ["DEVICE_ADMIN"] },
  { key: "users", href: "users.html", text: "人员", roles: ["DEVICE_ADMIN", "DEPT_ADMIN"] },
];

const ORDER_LIST_TITLE = {
  EMPLOYEE: "我的报修",
  DEPT_ADMIN: "部门工单",
  REPAIRER: "我的工单",
  DEVICE_ADMIN: "全部工单",
};

function renderTopbar(user, active) {
  const links = MENU.filter((m) => m.roles.includes(user.role)).map((m) => {
    const text = m.key === "orders" ? ORDER_LIST_TITLE[user.role] : m.text;
    return `<a href="${m.href}" class="${m.key === active ? "active" : ""}" ${m.key === active ? 'aria-current="page"' : ""}>
      ${text}${m.badge ? `<span class="count hidden" data-badge="${m.badge}"></span>` : ""}</a>`;
  }).join("");
  return `
    <div class="topbar-inner">
      <a class="wordmark" href="${homeOf(user)}"><span class="wordmark-plate">CYF</span><span class="wordmark-name">捷修云</span></a>
      <nav class="nav" aria-label="主菜单">${links}</nav>
      <div class="who">
        <button class="who-btn" type="button" aria-haspopup="true" aria-expanded="false">
          <span>${esc(user.real_name)}</span><span class="role">${esc(user.role_label)}</span>${icon("chevronDown", "icon-sm")}
        </button>
        <div class="menu" role="menu">
          <div class="menu-head">${esc(user.dept_name)} · ${esc(user.factory_area)}<br>账号 ${esc(user.username)}</div>
          <button type="button" data-act="password">${icon("key")}修改密码</button>
          <button type="button" data-act="logout" class="danger">${icon("logout")}退出登录</button>
        </div>
      </div>
    </div>`;
}

function bindTopbar(bar) {
  const btn = $(".who-btn", bar);
  const menu = $(".menu", bar);
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    btn.setAttribute("aria-expanded", String(menu.classList.toggle("open")));
  });
  document.addEventListener("click", () => {
    menu.classList.remove("open");
    btn.setAttribute("aria-expanded", "false");
  });
  menu.addEventListener("click", async (e) => {
    const act = e.target.closest("[data-act]")?.dataset.act;
    if (act === "logout") {
      try { await api.post("/api/auth/logout"); } catch { /* token 已失效也允许退出 */ }
      clearSession();
      location.replace("login.html?reason=logout");
    }
    if (act === "password") openPasswordDialog();
  });
}

function openPasswordDialog() {
  openModal({
    title: "修改密码",
    confirmText: "保存",
    body: `
      <div class="field"><label>原密码</label><input class="input" type="password" name="old" autocomplete="current-password"></div>
      <div class="field"><label>新密码</label><input class="input" type="password" name="new" autocomplete="new-password" placeholder="至少 6 位"></div>
      <div class="field"><label>确认新密码</label><input class="input" type="password" name="again" autocomplete="new-password"></div>`,
    async onConfirm(el) {
      const [oldPwd, newPwd, again] = ["old", "new", "again"].map((n) => $(`[name=${n}]`, el).value);
      if (newPwd.length < 6) throw new Error("新密码至少 6 位");
      if (newPwd !== again) throw new Error("两次输入的新密码不一致");
      await api.put("/api/auth/password", { old_password: oldPwd, new_password: newPwd });
      toast("密码已修改，请重新登录");
      setTimeout(() => toLogin(), 900);
    },
  });
}

/** 菜单数量：派单显示待派单数，维修工作台显示待接单数 */
async function loadBadges(bar) {
  const badges = [...bar.querySelectorAll("[data-badge]")];
  if (!badges.length) return;
  try {
    const counts = await api.get("/api/orders/status-counts");
    badges.forEach((b) => {
      const n = counts[b.dataset.badge] || 0;
      b.textContent = n > 99 ? "99+" : n;
      b.classList.toggle("hidden", n === 0);
    });
  } catch { /* 角标失败不影响页面 */ }
}

// 页面即将跳转时返回一个永不完成的 Promise，让页面脚本安静地停在 await 处，而不是抛出错误
const HALT = new Promise(() => {});

/**
 * 挂载页面框架：在页面顶部插入导航条，并做登录与角色校验。
 * @param {{active: string, title: string | ((user) => string), roles?: string[]}} options
 * @returns {Promise<object>} 当前登录用户
 */
export async function mountLayout({ active, title, roles }) {
  if (!getToken()) {
    toLogin();
    return HALT;
  }
  let user = getUser();
  try {
    user = await api.get("/api/auth/me"); // 以服务端为准：角色被修改或账号被停用会立即生效
    saveSession(getToken(), user);
  } catch (err) {
    if (err.code === 401) return HALT; // http.js 已跳转登录页
  }
  const allowed = roles || MENU.find((m) => m.key === active)?.roles || ALL;
  if (!allowed.includes(user.role)) {
    toast("当前角色无权访问该页面，已返回首页", "warning");
    setTimeout(() => location.replace(homeOf(user)), 600);
    return HALT;
  }

  const pageTitle = typeof title === "function" ? title(user) : title;
  const bar = document.createElement("header");
  bar.className = "topbar";
  bar.innerHTML = renderTopbar(user, active);
  document.body.prepend(bar);
  document.title = `${pageTitle} · CYF捷修云`;
  bindTopbar(bar);
  loadBadges(bar);
  return user;
}
