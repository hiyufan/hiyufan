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

- 后端常用 Go、Python、Rust，前端用 Vue 和 React
  <br><sub><i>Go, Python and Rust on the back end; Vue and React on the front end.</i></sub>
- 给 **[Apache TVM](https://github.com/apache/tvm)** 和 **[kornia](https://github.com/kornia/kornia)** 提过 5 个 PR，都已合并
  <br><sub><i>5 merged PRs to Apache TVM and kornia.</i></sub>
- 自己的项目有 **[求原图](https://github.com/hiyufan/shizhen)**（在线原图 / 视频提取，已上线）、**[alcedo](https://github.com/hiyufan/alcedo)**（Rust 视频解析库） 和 **[eposctl](https://github.com/hiyufan/eposctl)**
  <br><sub><i>Side projects: shizhen (live at ynvan.com), alcedo and eposctl.</i></sub>
- 最近在学 LLM 推理和 RAG
  <br><sub><i>Currently learning LLM inference and RAG.</i></sub>
- 邮箱 **[hi@oiya.net](mailto:hi@oiya.net)**
  <br><sub><i>Email: hi@oiya.net</i></sub>

---

## 开源贡献 · Open Source Contributions

> 给自己在用的项目提交的上游修复 —— **5 个 PR，全部合并**。
> <br><sub><i>Fixes sent upstream to projects I actually use — 5 PRs, all merged.</i></sub>

### <img src="https://github.com/apache.png" width="20" align="center" /> [Apache TVM](https://github.com/apache/tvm) &nbsp;![stars](https://img.shields.io/github/stars/apache/tvm?style=flat-square&label=%E2%98%85&color=425066)&nbsp; 深度学习编译器 <sub><i>· deep learning compiler</i></sub>

| PR | 状态 | 修复内容 · What it fixes |
|:--|:--|:--|
| [**#20255**](https://github.com/apache/tvm/pull/20255) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | Relax 的 `reshape` 把字面 `0` 读作"沿用输入维度"（ONNX 语义），PyTorch 却表示真实的零维，导致空张量上的 `reshape` / `view` / `flatten` / `unflatten` 报错或**静默给出错误形状**。与 torch 逐例对照验证 2132 组静态 + 938 组动态形状，并顺带修掉 `RemoveRedundantReshape` 里的同源缺陷。<br><sub><i>Relax read a literal <code>0</code> as "copy this dim" where PyTorch means a real zero-sized dim, so empty-tensor reshapes raised or silently returned the wrong shape. Verified against torch on 2,132 static + 938 dynamic shapes; also fixed the same bug in <code>RemoveRedundantReshape</code>.</i></sub> |
| [**#20254**](https://github.com/apache/tvm/pull/20254) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | `torch.sort` / `argsort` 发出 int32 索引，而其他所有索引类算子都是 int64 —— 一张图里出现两种索引 dtype。<br><sub><i><code>torch.sort</code> / <code>argsort</code> emitted int32 indices while every other index op was int64 — one graph, two index dtypes.</i></sub> |
| [**#20245**](https://github.com/apache/tvm/pull/20245) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | `flatten` 不校验维度，越界的负 `start_dim` 不在调用处报错，而是在下游生成错误的 `reshape`。<br><sub><i><code>flatten</code> didn't validate dims, so a bad negative <code>start_dim</code> produced a broken <code>reshape</code> downstream instead of failing at the call site.</i></sub> |

### <img src="https://github.com/kornia.png" width="20" align="center" /> [kornia](https://github.com/kornia/kornia) &nbsp;![stars](https://img.shields.io/github/stars/kornia/kornia?style=flat-square&label=%E2%98%85&color=5C3EE8)&nbsp; 可微分计算机视觉 <sub><i>· differentiable computer vision</i></sub>

| PR | 状态 | 修复内容 · What it fixes |
|:--|:--|:--|
| [**#4140**](https://github.com/kornia/kornia/pull/4140) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | 零尺寸的 `resize` / `rescale` 抛 `ZeroDivisionError`，而 warp 类算子对同样参数返回空图像。现在与之对齐，并让空结果留在自动微分图上。经 512 组形状 / 精度 / 插值模式验证对合法输入零影响。<br><sub><i>Zero-size <code>resize</code> / <code>rescale</code> threw <code>ZeroDivisionError</code> where the warping ops return an empty image. Now aligned, with the result kept on the autograd graph. Verified inert across 512 combinations.</i></sub> |
| [**#4143**](https://github.com/kornia/kornia/pull/4143) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | `__all__` 列出了未绑定的名字，`from kornia.core import *` 直接崩溃。恢复绑定，并加了一条全仓库的导出名解析检查。<br><sub><i><code>__all__</code> listed unbound names, so <code>import *</code> crashed. Restored them and added a repo-wide check that every exported name resolves.</i></sub> |

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
