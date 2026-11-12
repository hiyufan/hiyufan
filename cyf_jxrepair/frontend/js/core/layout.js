// 页面框架：按角色生成侧边菜单、顶栏、用户菜单；同时负责页面级的登录与角色守卫
import { api } from "./http.js";
import { icon } from "./icons.js";
import { clearSession, getToken, getUser, homeOf, saveSession, toLogin } from "./session.js";
import { $, esc, openModal, toast } from "./ui.js";

const ALL = ["EMPLOYEE", "DEPT_ADMIN", "DEVICE_ADMIN", "REPAIRER"];

/** 菜单配置：roles 决定谁能看到；页面守卫也复用这份配置 */
export const MENU = [
  { group: "工作台" },
  { key: "dashboard", href: "dashboard.html", text: "统计看板", icon: "dashboard", roles: ["DEVICE_ADMIN", "DEPT_ADMIN"] },
  { key: "dispatch", href: "dispatch.html", text: "派单中心", icon: "send", roles: ["DEVICE_ADMIN"], badge: "pending" },
  { key: "workbench", href: "workbench.html", text: "维修工作台", icon: "hammer", roles: ["REPAIRER"], badge: "assigned" },
  { key: "report", href: "report.html", text: "我要报修", icon: "plus", roles: ["EMPLOYEE", "DEPT_ADMIN"] },
  { key: "orders", href: "orders.html", text: "工单列表", icon: "list", roles: ALL },
  { group: "资料" },
  { key: "knowledge", href: "knowledge.html", text: "维修知识库", icon: "book", roles: ALL },
  { key: "devices", href: "devices.html", text: "设备台账", icon: "cpu", roles: ["DEVICE_ADMIN"] },
  { key: "users", href: "users.html", text: "用户管理", icon: "users", roles: ["DEVICE_ADMIN", "DEPT_ADMIN"] },
];

const ORDER_LIST_TITLE = {
  EMPLOYEE: "我的报修",
  DEPT_ADMIN: "部门工单",
  REPAIRER: "我的工单",
  DEVICE_ADMIN: "全部工单",
};

function visibleMenu(role) {
  const items = MENU.filter((m) => m.group || m.roles.includes(role));
  // 去掉下面没有菜单项的分组标题
  return items.filter((m, i) => !m.group || (items[i + 1] && !items[i + 1].group));
}

function renderSidebar(user, active) {
  const links = visibleMenu(user.role).map((m) => {
    if (m.group) return `<div class="nav-group">${m.group}</div>`;
    const text = m.key === "orders" ? ORDER_LIST_TITLE[user.role] : m.text;
    return `<a href="${m.href}" class="${m.key === active ? "active" : ""}" data-key="${m.key}">
      ${icon(m.icon)}<span>${text}</span>${m.badge ? `<span class="badge-dot hidden" data-badge="${m.badge}"></span>` : ""}
    </a>`;
  }).join("");
  return `
    <a class="brand" href="${homeOf(user)}">
      <span class="brand-mark">${icon("wrench")}</span>
      <span><div class="brand-name">CYF捷修云</div><div class="brand-sub">报修工单管理系统</div></span>
    </a>
    <nav class="nav">${links}</nav>
    <div class="sidebar-foot"><strong>${esc(user.dept_name)}</strong>${esc(user.factory_area)} · ${esc(user.role_label)}</div>`;
}

function renderTopbar(user, title, crumb) {
  return `
    <button class="btn btn-ghost btn-sm menu-toggle" type="button" aria-label="展开菜单">${icon("menu")}</button>
    <div><div class="topbar-title">${esc(title)}</div></div>
    ${crumb ? `<div class="topbar-crumb">/ ${esc(crumb)}</div>` : ""}
    <div class="topbar-right">
      <div class="user-chip">
        <button type="button" aria-haspopup="true">
          <span class="avatar">${esc(user.real_name.slice(-2))}</span>
          <span class="user-meta"><b>${esc(user.real_name)}</b><span>${esc(user.role_label)}</span></span>
        </button>
        <div class="dropdown" role="menu">
          <button type="button" data-act="password">${icon("key")}修改密码</button>
          <button type="button" data-act="logout" class="danger">${icon("logout")}退出登录</button>
        </div>
      </div>
    </div>`;
}

function bindTopbar(shell) {
  const chip = $(".user-chip", shell);
  const dropdown = $(".dropdown", chip);
  chip.querySelector("button").addEventListener("click", (e) => {
    e.stopPropagation();
    dropdown.classList.toggle("open");
  });
  document.addEventListener("click", () => dropdown.classList.remove("open"));
  $(".menu-toggle", shell).addEventListener("click", () => shell.classList.toggle("nav-open"));

  dropdown.addEventListener("click", async (e) => {
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

/** 侧边栏角标：派单中心显示待派单数，维修工作台显示待接单数 */
async function loadBadges(shell) {
  const badges = [...shell.querySelectorAll("[data-badge]")];
  if (!badges.length) return;
  try {
    const counts = await api.get("/api/orders/status-counts");
    badges.forEach((b) => {
      const n = counts[b.dataset.badge.toUpperCase()] || 0;
      b.textContent = n > 99 ? "99+" : n;
      b.classList.toggle("hidden", n === 0);
    });
  } catch { /* 角标失败不影响页面 */ }
}

// 页面即将跳转时返回一个永不完成的 Promise，让页面脚本安静地停在 await 处，而不是抛出错误
const HALT = new Promise(() => {});

/**
 * 挂载页面框架。HTML 中 <main class="content"> 是页面内容，这里把它包进统一外壳。
 * @param {{active: string, title: string | ((user) => string), crumb?: string, roles?: string[]}} options
 * @returns {Promise<object>} 当前登录用户
 */
export async function mountLayout({ active, title, crumb, roles }) {
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
  const content = $("main.content");
  const shell = document.createElement("div");
  shell.className = "shell";
  shell.innerHTML = `
    <aside class="sidebar">${renderSidebar(user, active)}</aside>
    <div class="main"><header class="topbar">${renderTopbar(user, pageTitle, crumb)}</header></div>`;
  $(".main", shell).append(content);
  document.body.prepend(shell);
  document.title = `${pageTitle} · CYF捷修云`;
  bindTopbar(shell);
  loadBadges(shell);
  return user;
}
