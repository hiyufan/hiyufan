// 接口地址：默认与页面同源（由 FastAPI 同时托管前端）。
// 如用 VS Code Live Server 等单独打开前端，可在控制台执行
//   localStorage.setItem("cyf_api_base", "http://127.0.0.1:8000")
// 后刷新页面，后端已开启跨域访问。
const saved = (() => {
  try { return localStorage.getItem("cyf_api_base"); } catch { return null; }
})();

export const API_BASE = (saved || "").replace(/\/$/, "");
export const APP_NAME = "CYF捷修云";
export const TOKEN_KEY = "cyf_token";
export const USER_KEY = "cyf_user";
