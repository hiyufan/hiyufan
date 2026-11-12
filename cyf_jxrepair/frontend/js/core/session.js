// 登录状态：token 与用户信息保存在 localStorage，刷新页面、关闭标签页后依然保持登录
import { TOKEN_KEY, USER_KEY } from "./config.js";

function read(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

export function getToken() {
  return read(TOKEN_KEY);
}

export function getUser() {
  try { return JSON.parse(read(USER_KEY) || "null"); } catch { return null; }
}

export function saveSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** 各角色登录后的默认首页 */
export const HOME_BY_ROLE = {
  EMPLOYEE: "report.html",
  DEPT_ADMIN: "dashboard.html",
  DEVICE_ADMIN: "dashboard.html",
  REPAIRER: "workbench.html",
};

export function homeOf(user) {
  return HOME_BY_ROLE[user?.role] || "orders.html";
}

export function toLogin(reason) {
  clearSession();
  const back = encodeURIComponent(location.pathname.split("/").pop() + location.search);
  location.replace(`login.html?redirect=${back}${reason ? `&reason=${reason}` : ""}`);
}
