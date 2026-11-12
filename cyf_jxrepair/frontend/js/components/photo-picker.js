// 现场照片选择：点击或拖拽选择、即时预览、删除、前端预校验（格式/大小/数量）
// 前端校验只为及时提示，后端仍会再次校验，二者缺一不可
import { icon } from "../core/icons.js";
import { esc, toast } from "../core/ui.js";

const ACCEPT = ["image/jpeg", "image/png"];

export function createPhotoPicker(container, { maxCount = 3, maxMb = 5, existing = [] } = {}) {
  let files = []; // {file, url}
  let kept = [...existing]; // 驳回后重新提交时，原有照片的 URL

  const render = () => {
    const total = files.length + kept.length;
    container.innerHTML = `
      <div class="photo-picker">
        ${kept.map((url, i) => `
          <div class="photo-item"><img src="${esc(url)}" alt="原照片">
            <button type="button" class="remove" data-kept="${i}" aria-label="移除">${icon("x", "icon-sm")}</button>
            <span class="size">原照片</span></div>`).join("")}
        ${files.map((f, i) => `
          <div class="photo-item"><img src="${f.url}" alt="${esc(f.file.name)}">
            <button type="button" class="remove" data-index="${i}" aria-label="移除">${icon("x", "icon-sm")}</button>
            <span class="size">${(f.file.size / 1024 / 1024).toFixed(2)} MB</span></div>`).join("")}
        ${total < maxCount ? `
          <label class="photo-add" tabindex="0">
            ${icon("camera", "icon-lg")}<span>添加照片</span><span class="subtle">${total}/${maxCount}</span>
            <input type="file" accept=".jpg,.jpeg,.png" multiple>
          </label>` : ""}
      </div>`;
  };

  const add = (list) => {
    for (const file of list) {
      if (files.length + kept.length >= maxCount) {
        toast(`最多上传 ${maxCount} 张照片`, "warning");
        break;
      }
      if (!ACCEPT.includes(file.type)) {
        toast(`「${file.name}」不是 jpg / png 格式`, "warning");
        continue;
      }
      if (file.size > maxMb * 1024 * 1024) {
        toast(`「${file.name}」超过 ${maxMb}MB`, "warning");
        continue;
      }
      files.push({ file, url: URL.createObjectURL(file) });
    }
    render();
  };

  container.addEventListener("change", (e) => {
    if (e.target.type === "file") add([...e.target.files]);
  });
  container.addEventListener("click", (e) => {
    const btn = e.target.closest(".remove");
    if (!btn) return;
    if (btn.dataset.index !== undefined) {
      const [removed] = files.splice(Number(btn.dataset.index), 1);
      URL.revokeObjectURL(removed.url); // 释放预览占用的内存
    } else {
      kept = []; // 后端按"全部保留 / 全部替换"处理原照片，所以移除任意一张即移除全部原照片
      toast("已移除原照片，提交后将使用新上传的照片", "info");
    }
    render();
  });
  container.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.classList.contains("photo-add")) e.target.querySelector("input").click();
  });
  ["dragenter", "dragover"].forEach((type) => container.addEventListener(type, (e) => {
    e.preventDefault();
    container.querySelector(".photo-add")?.classList.add("dragover");
  }));
  container.addEventListener("dragleave", () => container.querySelector(".photo-add")?.classList.remove("dragover"));
  container.addEventListener("drop", (e) => {
    e.preventDefault();
    add([...e.dataTransfer.files]);
  });

  render();
  return {
    getFiles: () => files.map((f) => f.file),
    keepsOriginal: () => kept.length > 0,
    reset() {
      files.forEach((f) => URL.revokeObjectURL(f.url));
      files = [];
      kept = [...existing];
      render();
    },
  };
}
