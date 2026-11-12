// 通用 UI 工具：转义、格式化、消息提示、确认弹窗、表单弹窗、按钮加载态
import { icon } from "./icons.js";

/** HTML 转义：所有用户输入的内容渲染前都必须经过它，防止 XSS */
export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function debounce(fn, wait = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

// ------------------------------------------------------------ 格式化
const pad = (n) => String(n).padStart(2, "0");

export function fmtTime(value, withYear = false) {
  if (!value) return "—";
  const d = new Date(value);
  const date = `${withYear ? `${d.getFullYear()}-` : ""}${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  return `${date} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fromNow(value) {
  if (!value) return "";
  const minutes = Math.round((Date.now() - new Date(value).getTime()) / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)} 小时前`;
  if (minutes < 60 * 24 * 30) return `${Math.floor(minutes / 1440)} 天前`;
  return fmtTime(value, true).slice(0, 10);
}

export function duration(start, end) {
  if (!start || !end) return "—";
  const hours = (new Date(end) - new Date(start)) / 3600000;
  return hours >= 1 ? `${hours.toFixed(1)} 小时` : `${Math.max(1, Math.round(hours * 60))} 分钟`;
}

export const statusTag = (code, label) => `<span class="tag st-${esc(code)}">${esc(label)}</span>`;
export const urgencyTag = (code, label) => `<span class="urg urg-${esc(code)}">${esc(label)}</span>`;

export function emptyState(title = "暂无数据", desc = "", iconName = "inbox") {
  return `<div class="empty">${icon(iconName)}<b>${esc(title)}</b>${desc ? `<span>${esc(desc)}</span>` : ""}</div>`;
}

export function skeletonRows(cols, rows = 5) {
  const cells = Array.from({ length: cols }, () => '<td><div class="skeleton"></div></td>').join("");
  return Array.from({ length: rows }, () => `<tr>${cells}</tr>`).join("");
}

// ------------------------------------------------------------ 消息提示
const TOAST_ICON = { success: "checkCircle", error: "xCircle", warning: "alert", info: "info" };

export function toast(message, type = "success", ms = 2600) {
  let stack = $(".toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "toast-stack";
    stack.setAttribute("role", "status");
    document.body.append(stack);
  }
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.innerHTML = `${icon(TOAST_ICON[type])}<span>${esc(message)}</span>`;
  stack.append(el);
  setTimeout(() => {
    el.classList.add("leaving");
    el.addEventListener("animationend", () => el.remove(), { once: true });
  }, type === "error" ? ms + 1400 : ms);
}

/** 统一错误提示：接口错误显示后端 message，其余显示通用文案 */
export function showError(err) {
  console.error(err);
  toast(err?.message || "操作失败，请稍后重试", "error");
}

// ------------------------------------------------------------ 按钮加载态
export async function withLoading(button, task) {
  if (!button) return task();
  const original = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span class="spinner"></span>${esc(button.textContent.trim())}`;
  try {
    return await task();
  } finally {
    button.disabled = false;
    button.innerHTML = original;
  }
}

// ------------------------------------------------------------ 弹窗
/**
 * 打开弹窗。onConfirm 返回 Promise：成功则关闭；抛错则保持打开并提示，用户无需重新填写。
 * @returns {{el: HTMLElement, close: Function}}
 */
export function openModal({ title, body = "", confirmText = "确定", cancelText = "取消", danger = false,
  wide = false, onConfirm, onOpen, onClose, footer = true }) {
  const mask = document.createElement("div");
  mask.className = "modal-mask";
  mask.innerHTML = `
    <div class="modal ${wide ? "wide" : ""}" role="dialog" aria-modal="true" aria-label="${esc(title)}">
      <div class="modal-head"><h3>${esc(title)}</h3>
        <button class="btn btn-ghost btn-sm close" type="button" aria-label="关闭">${icon("x")}</button></div>
      <div class="modal-body">${body}</div>
      ${footer ? `<div class="modal-foot">
        <button class="btn" type="button" data-cancel>${esc(cancelText)}</button>
        <button class="btn ${danger ? "btn-danger solid" : "btn-primary"}" type="button" data-ok>${esc(confirmText)}</button>
      </div>` : ""}
    </div>`;
  const prevFocus = document.activeElement;

  const close = () => {
    mask.remove();
    onClose?.();
    document.removeEventListener("keydown", onKey);
    prevFocus?.focus?.();
  };
  const onKey = (e) => { if (e.key === "Escape") close(); };

  mask.addEventListener("mousedown", (e) => { if (e.target === mask) close(); });
  mask.querySelector(".close").addEventListener("click", close);
  mask.querySelector("[data-cancel]")?.addEventListener("click", close);
  const okBtn = mask.querySelector("[data-ok]");
  okBtn?.addEventListener("click", async () => {
    if (!onConfirm) return close();
    try {
      const keepOpen = await withLoading(okBtn, () => onConfirm(mask));
      if (keepOpen !== false) close();
    } catch (err) {
      showError(err);
    }
  });
  document.addEventListener("keydown", onKey);
  document.body.append(mask);
  onOpen?.(mask);
  (mask.querySelector("input, textarea, select") || okBtn)?.focus();
  return { el: mask, close };
}

export function confirmDialog({ title, message, confirmText = "确定", danger = false }) {
  // 无论点"确定"、"取消"、遮罩还是按 Esc 关闭，Promise 都会被 resolve
  return new Promise((resolve) => {
    let confirmed = false;
    openModal({
      title, confirmText, danger,
      body: `<p class="modal-intro">${esc(message)}</p>`,
      onConfirm: () => { confirmed = true; },
      onClose: () => resolve(confirmed),
    });
  });
}

/** 表单字段校验提示：在字段下方显示红字并高亮边框 */
export function fieldError(field, message) {
  const wrap = field.closest(".field");
  if (!wrap) return;
  wrap.classList.toggle("invalid", Boolean(message));
  let tip = wrap.querySelector(".error-text");
  if (!tip) {
    tip = document.createElement("div");
    tip.className = "error-text";
    wrap.append(tip);
  }
  tip.textContent = message || "";
}

export function clearFieldErrors(root) {
  $$(".field.invalid", root).forEach((f) => f.classList.remove("invalid"));
  $$(".error-text", root).forEach((t) => { t.textContent = ""; });
}
