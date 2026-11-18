// 保留独立 HTML 入口，站内切换仅替换内容区；页面模块可重复挂载和退出。
import { closeModals, showError } from "./ui.js";

const pages = {
  "dashboard.html": () => import("../pages/dashboard.js"),
  "dispatch.html": () => import("../pages/dispatch.js"),
  "workbench.html": () => import("../pages/workbench.js"),
  "report.html": () => import("../pages/report.js"),
  "orders.html": () => import("../pages/orders.js"),
  "order-detail.html": () => import("../pages/order-detail.js"),
  "knowledge.html": () => import("../pages/knowledge.js"),
  "knowledge-detail.html": () => import("../pages/knowledge-detail.js"),
  "devices.html": () => import("../pages/devices.js"),
  "users.html": () => import("../pages/users.js"),
};
const templates = new Map();
const appBase = new URL("../../", import.meta.url);
const initialRoot = document.querySelector("main.content");
templates.set(location.pathname, { html: initialRoot.outerHTML, title: document.title });
let pending;
let view;
let chartsReady;

function routeOf(url) {
  if (url.origin !== location.origin) return null;
  // 只接管明确的应用页面，图片、接口文档、外链保留浏览器行为。
  if (!url.pathname.startsWith(appBase.pathname)) return null;
  return url.pathname.slice(appBase.pathname.length).match(/^([\w-]+\.html)$/)?.[1] || null;
}

async function templateOf(url, signal) {
  if (templates.has(url.pathname)) return templates.get(url.pathname);
  const response = await fetch(url.pathname, { signal });
  if (!response.ok) throw new Error(`页面加载失败（HTTP ${response.status}），请稍后重试`);
  const doc = new DOMParser().parseFromString(await response.text(), "text/html");
  const main = doc.querySelector("main.content");
  if (!main) throw new Error("页面内容不完整，请刷新后重试");
  const template = { html: main.outerHTML, title: doc.title };
  templates.set(url.pathname, template);
  return template;
}

function loadCharts() {
  if (window.echarts) return Promise.resolve();
  chartsReady ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = new URL("lib/echarts.min.js", appBase).href;
    script.onload = resolve;
    script.onerror = () => { chartsReady = null; script.remove(); reject(new Error("图表组件加载失败，请重试")); };
    document.head.append(script);
  });
  return chartsReady;
}

async function render(href, { replace = false, initial = false, pop = false } = {}) {
  const url = new URL(href, location.href);
  const route = routeOf(url);
  if (!pages[route]) return;
  pending?.abort();
  const controller = new AbortController();
  pending = controller;
  const { signal } = controller;
  document.documentElement.classList.add("navigating");
  try {
    const [template, module] = await Promise.all([
      templateOf(url, signal), pages[route](), route === "dashboard.html" ? loadCharts() : null,
    ]);
    signal.throwIfAborted();
    view?.abort();
    closeModals();
    if (!initial) {
      const holder = document.createElement("template");
      holder.innerHTML = template.html;
      document.querySelector("main.content").replaceWith(holder.content.firstElementChild);
    }
    if (!pop) {
      const state = { appRoute: true, from: initial ? null : location.pathname + location.search };
      if (initial || replace) history.replaceState(state, "", url);
      else history.pushState(state, "", url);
    }
    document.title = template.title;
    const root = document.querySelector("main.content");
    root.setAttribute("aria-busy", "true");
    view = controller;
    await module.mount({ root, signal });
    signal.throwIfAborted();
    root.removeAttribute("aria-busy");
    if (!initial) {
      window.scrollTo(0, 0);
      root.setAttribute("tabindex", "-1");
      root.focus({ preventScroll: true });
    }
  } catch (err) {
    if (!signal.aborted) showError(err);
  } finally {
    if (pending === controller) {
      pending = null;
      document.documentElement.classList.remove("navigating");
      document.querySelector("main.content")?.removeAttribute("aria-busy");
    }
  }
}

document.addEventListener("click", (event) => {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const link = event.target.closest("a[href]");
  if (!link || link.hasAttribute("download") || (link.target && link.target !== "_self")) return;
  const url = new URL(link.href);
  if (!pages[routeOf(url)]) return;
  event.preventDefault();
  if (url.href !== location.href || pending) render(url.href);
});
document.addEventListener("app:navigate", (event) => {
  if (!pages[routeOf(new URL(event.detail.href, location.href))]) return;
  event.preventDefault();
  render(event.detail.href, event.detail);
});
window.addEventListener("popstate", () => render(location.href, { pop: true }));
render(location.href, { initial: true });
