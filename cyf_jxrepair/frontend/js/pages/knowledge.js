// 维修知识库检索：TF-IDF 相似度排序，结果中高亮命中的字词
import { api } from "../core/http.js";
import { icon } from "../core/icons.js";
import { mountLayout } from "../core/layout.js";
import { $, emptyState, esc, fmtTime, showError } from "../core/ui.js";

await mountLayout({ active: "knowledge", title: "维修知识库" });

const HOT = ["异响", "漏油", "跳闸", "温度过高", "皮带跑偏", "伺服报警", "气压不足", "无法启动"];
$("#searchBox").insertAdjacentHTML("afterbegin", icon("search"));
$("#hot").innerHTML = `<span class="subtle">常见故障：</span>${HOT.map((k) => `<button type="button" class="chip-btn" data-q="${k}">${k}</button>`).join("")}`;

/** 高亮查询词中的二字片段（与后端"字二元组"切分思路一致）。先匹配原文再逐段转义，保证不破坏 HTML */
function highlight(text, query) {
  const q = query.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, "");
  const grams = [...new Set(Array.from({ length: Math.max(q.length - 1, 0) }, (_, i) => q.slice(i, i + 2)))];
  if (!grams.length) return esc(text);
  const pattern = new RegExp(`(?:${grams.map((g) => g.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})+`, "gi");
  let html = "";
  let last = 0;
  for (const m of text.matchAll(pattern)) {
    html += `${esc(text.slice(last, m.index))}<mark>${esc(m[0])}</mark>`;
    last = m.index + m[0].length;
  }
  return html + esc(text.slice(last));
}

async function search(query) {
  const q = query.trim();
  const params = new URLSearchParams(location.search);
  if (q) params.set("q", q); else params.delete("q");
  history.replaceState(null, "", `${location.pathname}${params.toString() ? `?${params}` : ""}`);
  if (q.length < 2) {
    $("#results").innerHTML = emptyState("输入故障现象开始检索", "至少 2 个字，描述越具体结果越准", "book");
    return;
  }
  $("#results").innerHTML = '<div style="padding:20px 24px"><div class="skeleton"></div></div>';
  try {
    const hits = await api.get("/api/ai/knowledge", { q, top_k: 10 });
    $("#results").innerHTML = hits.length ? hits.map((h) => `
      <article class="kb-result">
        <h4><a href="order-detail.html?id=${h.order_id}">${esc(h.device_name)}</a><span class="chip">${esc(h.category)}</span>
          <span class="mono subtle">${esc(h.order_no)}</span><span class="subtle">· 归档于 ${fmtTime(h.archived_at, true).slice(0, 10)}</span></h4>
        <div class="score-ring"><b>${Math.round(h.score * 100)}%</b><span>相似度</span></div>
        <dl class="qa"><dt>现象</dt><dd>${highlight(h.fault_desc, q)}</dd><dt>处理</dt><dd>${highlight(h.repair_result, q)}</dd></dl>
      </article>`).join("") : emptyState("没有找到相似案例", "可以换一种描述方式，或直接提交报修", "search");
  } catch (err) {
    showError(err);
  }
}

$("#searchForm").addEventListener("submit", (e) => { e.preventDefault(); search($("#q").value); });
$("#hot").addEventListener("click", (e) => {
  const chip = e.target.closest("[data-q]");
  if (!chip) return;
  $("#q").value = chip.dataset.q;
  search(chip.dataset.q);
});

const initial = new URLSearchParams(location.search).get("q") || "";
$("#q").value = initial;
search(initial);
