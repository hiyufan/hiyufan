<img src="https://capsule-render.vercel.app/api?type=waving&color=0:4FC08D,100:2F80ED&height=200&section=header&text=Hi%20there,%20I%27m%20Yufan&fontSize=46&fontColor=ffffff&fontAlignY=36&desc=AI%20student%20%C2%B7%20Full-stack%20developer&descSize=18&descAlignY=56&animation=fadeIn" width="100%" alt="header" />

<div align="center">

<a href="https://github.com/hiyufan">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=20&duration=3000&pause=1000&color=2F9E6E&center=true&vCenter=true&width=560&lines=AI+student;Full-stack+developer;Rust+%C2%B7+Go+%C2%B7+Python+%C2%B7+TypeScript;Contributor+to+Apache+TVM+%26+kornia" alt="Typing SVG" />
</a>

<img src="https://skillicons.dev/icons?i=rust,go,py,ts,vue,react,pytorch,fastapi,docker,linux,git&perline=11" alt="skills" />
<br><br>

<img src="https://komarev.com/ghpvc/?username=hiyufan&label=Profile%20views&color=4FC08D&style=flat-square" alt="profile views" />

</div>

---

## 关于我 · About Me

人工智能专业在读，平时主要做全栈开发，前端后端都写。

<sub><i>AI student. I mostly do full-stack development, front end and back end.</i></sub>

- 邮箱 **[hi@oiya.net](mailto:hi@oiya.net)**
  <br><sub><i>Email: hi@oiya.net</i></sub>

---

## 开源贡献 · Open Source Contributions

> 参与上游代码修复和功能补充 —— **8 个 PR，均已合并**。
> <br><sub><i>Upstream fixes and new features — 8 merged PRs.</i></sub>

### <img src="https://github.com/apache.png" width="20" align="center" /> [Apache TVM](https://github.com/apache/tvm) &nbsp;![stars](https://img.shields.io/github/stars/apache/tvm?style=flat-square&label=%E2%98%85&color=425066)&nbsp; 深度学习编译器 <sub><i>· deep learning compiler</i></sub>

| PR | 状态 | 修复内容 · What it fixes |
|:--|:--|:--|
| [**#20818**](https://github.com/apache/tvm/pull/20818) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | 为 Relax ONNX 前端新增 `LpNormalization` 转换，支持 L1 / L2 归一化；处理零范数切片，并让 float16 / bfloat16 输入在 float32 中计算以避免溢出。<br><sub><i>Added ONNX <code>LpNormalization</code> support for L1 / L2 norms, including zero-norm slices and float32 computation for float16 / bfloat16 inputs.</i></sub> |
| [**#20816**](https://github.com/apache/tvm/pull/20816) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | 修复 `RemoveUnusedOutputs` 在元组返回值均未使用时误删有副作用调用的问题，保留 `R.print` 等操作及原返回签名。<br><sub><i>Fixed <code>RemoveUnusedOutputs</code> dropping impure calls when all tuple outputs are unused, preserving side effects such as <code>R.print</code> and the return signature.</i></sub> |
| [**#20815**](https://github.com/apache/tvm/pull/20815) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | 修复 `ReorderTakeAfterMatmul` 对一维权重的错误重排，避免沿归约轴取值被移到矩阵乘法之后而导致崩溃或静默算错。<br><sub><i>Prevented an invalid <code>ReorderTakeAfterMatmul</code> rewrite for vector weights that caused crashes or silently incorrect results.</i></sub> |
| [**#20255**](https://github.com/apache/tvm/pull/20255) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | Relax 将目标形状中的字面 `0` 解释为复制输入维度，与 PyTorch 的真实零尺寸语义不同。修复空张量的 `reshape` / `view` / `flatten` / `unflatten`，以及 `RemoveRedundantReshape` 优化中重新解释零维导致的形状错误。<br><sub><i>Fixed zero-sized tensor shapes in PyTorch reshape, view, flatten and unflatten imports, plus a <code>RemoveRedundantReshape</code> rewrite that changed the meaning of literal zeros.</i></sub> |
| [**#20254**](https://github.com/apache/tvm/pull/20254) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | `torch.sort` / `argsort` 发出 int32 索引，而其他所有索引类算子都是 int64 —— 一张图里出现两种索引 dtype。<br><sub><i><code>torch.sort</code> / <code>argsort</code> emitted int32 indices while every other index op was int64 — one graph, two index dtypes.</i></sub> |
| [**#20245**](https://github.com/apache/tvm/pull/20245) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | `flatten` 不校验维度，越界的负 `start_dim` 不在调用处报错，而是在下游生成错误的 `reshape`。<br><sub><i><code>flatten</code> didn't validate dims, so a bad negative <code>start_dim</code> produced a broken <code>reshape</code> downstream instead of failing at the call site.</i></sub> |
| **结果 · Results** | **6 个已合并 PR**<br><sub>6 merged PRs</sub> | **模型兼容**：新增 1 个 ONNX 算子 `LpNormalization`，支持 L1 / L2 两种归一化及 float16、bfloat16、float32、float64 四种精度（[#20818](https://github.com/apache/tvm/pull/20818)）；修复 `reshape` / `view` / `flatten` / `unflatten` 四类形状操作的空张量兼容问题（[#20255](https://github.com/apache/tvm/pull/20255)）；将 `sort` / `argsort` 两个算子的索引从 int32 修正为 PyTorch 要求的 int64（[#20254](https://github.com/apache/tvm/pull/20254)）。<br>**形状正确性**：在 [#20255 的 938 组动态形状复现扫描](https://github.com/apache/tvm/pull/20255#issuecomment-5602705518)中，符号目标修复将不匹配数从 **360 降至 46，减少 87.2%**；另消除冗余 reshape 优化引入的 **24 组错误**（[70 → 46](https://github.com/apache/tvm/pull/20255#issuecomment-5653375303)）。剩余 46 组包含 40 组已有异常和 6 组表达式格式差异。<br>**编译正确性**：修复 3 个编译优化流程中的问题，分别保留未使用返回值的有副作用调用、阻止向量权重的错误重排、避免合并 reshape 时改变零尺寸形状（[#20816](https://github.com/apache/tvm/pull/20816)、[#20815](https://github.com/apache/tvm/pull/20815)、[#20255](https://github.com/apache/tvm/pull/20255)）。<br><sub><i>Added 1 ONNX operator with 2 normalization modes and 4 floating-point dtypes; fixed empty-tensor compatibility for 4 shape operations and corrected index dtypes in 2 sorting operators. In the PR’s 938-case dynamic-shape reproducer sweep, the symbolic-target fix reduced mismatches from 360 to 46 (87.2%); the reshape-pass fix separately eliminated 24 pass-induced errors (70 to 46). The remaining 46 comprise 40 pre-existing errors and 6 expression-format differences. Fixed 3 compiler passes to preserve side effects and prevent incorrect vector-weight rewrites and zero-sized reshape fusion.</i></sub> |

### <img src="https://github.com/kornia.png" width="20" align="center" /> [kornia](https://github.com/kornia/kornia) &nbsp;![stars](https://img.shields.io/github/stars/kornia/kornia?style=flat-square&label=%E2%98%85&color=5C3EE8)&nbsp; 可微分计算机视觉 <sub><i>· differentiable computer vision</i></sub>

| PR | 状态 | 修复内容 · What it fixes |
|:--|:--|:--|
| [**#4140**](https://github.com/kornia/kornia/pull/4140) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | 修复零尺寸输出的 `resize` / `rescale` 抛出 `ZeroDivisionError` 的问题，返回保留自动微分连接的空图像；对无法调整到正尺寸的退化输入给出明确的 `ValueError`。<br><sub><i>Made zero-sized resize / rescale outputs return empty images with an autograd connection, and reject degenerate inputs when a positive output size is requested.</i></sub> |
| [**#4143**](https://github.com/kornia/kornia/pull/4143) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | 恢复 `kornia.core` 中 `eye_like` / `vec_like` 的导出绑定，移除 `kornia.color.__all__` 中已失效的 `AUTUMN` 条目，并新增全包公开名称解析检查，修复两处 `import *` 失败。<br><sub><i>Restored the <code>eye_like</code> / <code>vec_like</code> exports, removed the stale <code>AUTUMN</code> entry and added a package-wide public-name guard, fixing star imports in core and color.</i></sub> |
| **结果 · Results** | **2 个已合并 PR**<br><sub>2 merged PRs</sub> | **图像处理**：`resize` / `rescale` / `Resize` / `Rescale` **4 个接口**对零尺寸输出从抛出异常改为返回空图像，并保留自动微分连接，使输出退化为空时仍可参与反向传播（[#4140](https://github.com/kornia/kornia/pull/4140)）。<br>**公开 API**：恢复 `eye_like` / `vec_like` 两个导出绑定，移除 1 个失效的 `AUTUMN` 声明，使 `kornia.core` / `kornia.color` **2 个模块**的 `import *` 从报错恢复正常；新增自动检查所有可导入且声明 `__all__` 的子模块，防止同类缺陷再次漏检（[#4143](https://github.com/kornia/kornia/pull/4143)）。<br><sub><i>Made 4 resizing APIs return autograd-connected empty images instead of raising on zero-sized outputs. Restored 2 export bindings, removed 1 stale declaration and fixed star imports in 2 modules; added export checks across all importable submodules declaring <code>__all__</code>.</i></sub> |

---

## 项目 · Featured Projects

| 项目 | 说明 · Description | 技术栈 |
|:--|:--|:--|
| [**求原图**](https://github.com/hiyufan/shizhen) | 粘贴分享链接下载原图和视频，可截一段转 GIF、实况照片。支持抖音、小红书、YouTube、B站等 30 多个平台，也能提取 Steam 动态头像、音乐封面、游戏壁纸。已上线 [ynvan.com](https://ynvan.com)，可自部署<br><sub><i>Paste a share link to save the original video or images, or turn a clip into a GIF / Live Photo. 30+ platforms, plus Steam avatars, album covers and game wallpapers. Live at ynvan.com, self-hostable.</i></sub> | `Python` `FastAPI` `Docker` |
| [**alcedo**](https://github.com/hiyufan/alcedo) | 高性能视频平台解析核心，35 个平台，纯 Rust 零外部进程依赖<br><sub><i>High-performance video parsing core for 35 platforms — pure Rust, zero external processes.</i></sub> | `Rust` |
| [**eposctl**](https://github.com/hiyufan/eposctl) | EPOS Gaming Suite 停更后的开源替代：EQ、预设、7.1 环绕、麦克风、电量，一个免安装的 exe<br><sub><i>Open-source replacement for the discontinued EPOS Gaming Suite: EQ, presets, surround, mic and battery in one portable exe.</i></sub> | `Rust` `Windows` |
| **yf-quant** <sub>(private)</sub> | 基于 Qlib 的美股量化研究平台<br><sub><i>US equities quant research platform built on Qlib.</i></sub> | `Python` `Qlib` |
| [**edubridge**](https://github.com/hiyufan/edubridge) | 高校教务系统中间件<br><sub><i>Middleware for university academic systems.</i></sub> | `Go` `Vue` |

---

## 正在学 · Currently Learning

<table>
<tr>
<td width="50%" valign="top">

**RAG · 检索增强生成**
<br><sub>分块与召回策略、重排序、评测方法</sub>
<br><sub><i>Chunking & retrieval, reranking, evaluation</i></sub>

</td>
<td width="50%" valign="top">

**LLM 推理引擎**
<br><sub>vLLM / SGLang 的调度与显存管理</sub>
<br><sub><i>Scheduling & KV-cache management in vLLM / SGLang</i></sub>

</td>
</tr>
</table>

---

## 数据 · GitHub Stats

<div align="center">

<img src="https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username=hiyufan&theme=github" width="86%" />

<img height="170" src="https://github-profile-summary-cards.vercel.app/api/cards/repos-per-language?username=hiyufan&theme=github" />
<img height="170" src="https://github-profile-summary-cards.vercel.app/api/cards/most-commit-language?username=hiyufan&theme=github" />

<img height="170" src="https://streak-stats.demolab.com?user=hiyufan&hide_border=true&background=00000000&ring=4FC08D&fire=EE4C2C&currStreakLabel=4FC08D" />

</div>

### 贡献图 · Contribution Graph

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/hiyufan/hiyufan/output/github-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/hiyufan/hiyufan/output/github-snake.svg" />
  <img alt="contribution snake animation" src="https://raw.githubusercontent.com/hiyufan/hiyufan/output/github-snake.svg" />
</picture>

</div>

---

<div align="center">

### 联系 · Let's Connect

[![Email](https://img.shields.io/badge/hi@oiya.net-0078D4?style=flat-square&logo=gmail&logoColor=white)](mailto:hi@oiya.net)
[![GitHub](https://img.shields.io/badge/@hiyufan-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/hiyufan)

<sub>欢迎交流全栈开发、AI 和开源。</sub><br>
<sub><i>Happy to chat about full-stack dev, AI, and open source.</i></sub>

</div>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:4FC08D,100:2F80ED&height=110&section=footer" width="100%" alt="footer" />
