// 分页组件：renderPager(容器, {page, size, total}, 翻页回调)
import { icon } from "../core/icons.js";

function pageList(current, totalPages) {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
  const pages = new Set([1, totalPages, current, current - 1, current + 1]);
  if (current <= 3) [2, 3, 4].forEach((p) => pages.add(p));
  if (current >= totalPages - 2) [totalPages - 1, totalPages - 2, totalPages - 3].forEach((p) => pages.add(p));
  const sorted = [...pages].filter((p) => p >= 1 && p <= totalPages).sort((a, b) => a - b);
  // 不连续处插入省略号
  return sorted.flatMap((p, i) => (i && p - sorted[i - 1] > 1 ? ["…", p] : [p]));
}

export function renderPager(container, { page, size, total }, onChange) {
  const totalPages = Math.max(1, Math.ceil(total / size));
  const from = total ? (page - 1) * size + 1 : 0;
  const to = Math.min(page * size, total);
  container.innerHTML = `
    <div class="pager">
      <span class="pager-info">共 <b class="num">${total}</b> 条，当前 ${from}-${to}</span>
      <div class="pager-btns">
        <button type="button" data-page="${page - 1}" ${page <= 1 ? "disabled" : ""} aria-label="上一页">${icon("chevronLeft", "icon-sm")}</button>
        ${pageList(page, totalPages).map((p) => (p === "…"
          ? '<span class="gap">…</span>'
          : `<button type="button" data-page="${p}" class="${p === page ? "active" : ""}">${p}</button>`)).join("")}
        <button type="button" data-page="${page + 1}" ${page >= totalPages ? "disabled" : ""} aria-label="下一页">${icon("chevronRight", "icon-sm")}</button>
      </div>
    </div>`;
  container.onclick = (e) => {
    const btn = e.target.closest("button[data-page]");
    if (!btn || btn.disabled) return;
    const target = Number(btn.dataset.page);
    if (target !== page) onChange(target);
  };
}
