// 页面与路由之间的轻量接口；登录、外链等仍可使用浏览器原生跳转。
export function navigate(href, { replace = false } = {}) {
  const event = new CustomEvent("app:navigate", { cancelable: true, detail: { href, replace } });
  if (document.dispatchEvent(event)) {
    if (replace) location.replace(href);
    else location.assign(href);
  }
}
