// 统一请求封装：自动携带 token、解析 {code, message, data}、处理登录失效
import { API_BASE } from "./config.js";
import { getToken, toLogin } from "./session.js";

export class ApiError extends Error {
  constructor(message, code, data) {
    super(message);
    this.code = code;
    this.data = data;
  }
}

function buildUrl(path, params) {
  const url = new URL(API_BASE + path, location.origin);
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    // 数组参数展开为 ?status=A&status=B
    (Array.isArray(value) ? value : [value]).forEach((v) => url.searchParams.append(key, v));
  });
  return url;
}

async function request(method, path, { params, json, form, signal } = {}) {
  signal?.throwIfAborted();
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body;
  if (form) {
    body = form; // FormData：浏览器自动设置 multipart 边界，不能手动指定 Content-Type
  } else if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }

  let resp;
  try {
    resp = await fetch(buildUrl(path, params), { method, headers, body, signal });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new ApiError("无法连接服务器，请确认后端已启动", 0);
  }

  let payload;
  try {
    payload = await resp.json();
  } catch {
    signal?.throwIfAborted();
    throw new ApiError(`服务器返回异常（HTTP ${resp.status}）`, resp.status);
  }

  signal?.throwIfAborted();
  // 只有携带了 token 的请求返回 401 才说明登录过期；登录接口本身的 401 是"账号或密码错误"，交给页面显示
  if (payload.code === 401 && token) {
    toLogin("expired");
    throw new ApiError(payload.message, 401);
  }
  if (payload.code !== 200) {
    throw new ApiError(payload.message || "请求失败", payload.code, payload.data);
  }
  return payload.data;
}

export const createApi = (signal) => ({
  get: (path, params) => request("GET", path, { params, signal }),
  post: (path, json) => request("POST", path, { json, signal }),
  put: (path, json) => request("PUT", path, { json, signal }),
  patch: (path, json) => request("PATCH", path, { json, signal }),
  del: (path) => request("DELETE", path, { signal }),
  upload: (path, form) => request("POST", path, { form, signal }),
});
export const api = createApi();

/** 资源地址（图片等）补全为完整 URL */
export const assetUrl = (path) => (path?.startsWith("http") ? path : API_BASE + path);
