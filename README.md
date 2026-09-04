<div align="center">

# 陈雨钒 · Chen Yufan

**系统与 AI 基础设施** &nbsp;·&nbsp; *Systems & AI Infrastructure*

写编译器前端的补丁，也修别人的认证漏洞。<br>
<sub><i>Patching compiler frontends, and fixing other people's auth bypasses.</i></sub>

<br>

![Rust](https://img.shields.io/badge/Rust-000000?style=flat-square&logo=rust&logoColor=white)
![Go](https://img.shields.io/badge/Go-00ADD8?style=flat-square&logo=go&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)
<br>
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![Apache TVM](https://img.shields.io/badge/Apache%20TVM-425066?style=flat-square&logo=apache&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=flat-square&logo=git&logoColor=white)

<img src="https://komarev.com/ghpvc/?username=hiyufan&label=Profile%20views&color=4FC08D&style=flat-square" alt="profile views" />

</div>

---

## 🔧 开源贡献 · Open Source

> 给自己在用的项目提交的修复。链接指向 PR —— 部分仍在 review 中。
> <sub><i>Fixes sent to projects I use. Links go to the pull requests; some are still under review.</i></sub>

### [Apache TVM](https://github.com/apache/tvm) &nbsp;`13.7k ★`&nbsp; 深度学习编译器

[**#20245**](https://github.com/apache/tvm/pull/20245) — 修复 Relax PyTorch 前端 `flatten` 的参数校验缺陷。越界的负 `start_dim` **不在使用处报错**：它被归一化成 `-1`，把多余的一维折进乘积，发出形状错误的 `reshape`，直到下游才失败。补上范围与顺序校验、0 维张量支持和回归测试。

> <sub>Validate `flatten` dims in the Relax PyTorch frontend. An out-of-range negative `start_dim` silently computed a wrong shape that only failed further downstream in `reshape`. Added range and ordering checks, 0-d input support, and regression tests.</sub>

[**#20254**](https://github.com/apache/tvm/pull/20254) &nbsp;`✅ 已批准 approved`&nbsp; — `torch.sort` / `torch.argsort` 返回 int64 索引，前端却发 int32。同文件的 `_topk` 已经显式覆盖了同一个 int32 默认值，说明这是遗漏而非约定；前端支持的其他索引类算子（`argmax`、`argmin`、`max(dim)`、`median(dim)`、`bucketize`）也都是 int64。一张导入图会因此对同一种值带上两种索引 dtype。

> <sub>`torch.sort` / `torch.argsort` return int64 indices; the frontend emitted int32. `_topk` in the same file already overrides the identical default, and every other index-producing op comes out int64 — so one imported graph could carry two index dtypes for the same kind of value.</sub>

[**#20255**](https://github.com/apache/tvm/pull/20255) — Relax 的 `reshape` 把目标形状里的字面 `0` 读作"沿用输入对应维度"（ONNX `allowzero=0` 语义），PyTorch 读作真实的零维。空张量上的 `reshape` / `view` / `flatten` / `unflatten` 因此报错或**静默给出错误形状**；`flatten` 在 `(0,3)` 上恰好正确，正是这个巧合掩盖了其余情形。经与 torch 逐例对照 2132 组静态形状 + 63 组符号形状验证。

> <sub>Relax's `reshape` reads a literal `0` as "copy the input dimension" (ONNX `allowzero=0`) where PyTorch reads a real zero-sized one, so `reshape` / `view` / `flatten` / `unflatten` on empty tensors raised or silently produced a wrong shape. Verified against torch across 2132 static and 63 symbolic shape cases.</sub>

### [Feast](https://github.com/feast-dev/feast) &nbsp;`7.2k ★`&nbsp; Linux Foundation AI & Data

[**#6801**](https://github.com/feast-dev/feast/pull/6801) — 修复 RBAC 完全绕过漏洞（公告 `GHSA-h543-6vgr-fm36`，[issue #6785](https://github.com/feast-dev/feast/issues/6785)）。两个 token 解析器都从**未验签**的 JWT 解码中授予完全信任的内部身份，而对比值硬编码在 Feast 官方 Helm chart 里 —— 任何能访问到服务的人都能伪造它，跳过该服务上**所有项目的所有权限检查**。改为对内部 token 签名、密钥移入 Kubernetes Secret 且不提供默认值、未配置时 fail closed。

> <sub>Fix an RBAC bypass. Both token parsers granted a fully trusted internal identity from an <i>unverified</i> JWT decode, compared against a value hardcoded in Feast's own Helm chart. Signed the internal token, moved the secret to a Kubernetes Secret with no default, and made an unset secret fail closed.</sub>

[**#6803**](https://github.com/feast-dev/feast/pull/6803) — 修复离线服务器的项目上下文泄漏。`set_current_project` 设置的 `ContextVar` 从不重置，一个请求的项目会残留到同一 worker 上后续未指定项目的请求里。改为 `try` / `finally` 配对重置，覆盖 `_call_api` 与 `do_get` 两条路径。

> <sub>Fix a project-context leak in the offline server. The `ContextVar` set per request was never reset, so one request's project persisted into later requests on the same worker. Paired it with a `finally` reset on both entry points.</sub>

### [kornia](https://github.com/kornia/kornia) &nbsp;`11.3k ★`&nbsp; 可微分计算机视觉

[**#4140**](https://github.com/kornia/kornia/pull/4140) — 统一 `resize` / `rescale` 的零尺寸语义。它们对零尺寸输出抛裸 `ZeroDivisionError`，而 `warp_affine`、`warp_perspective`、`center_crop` 对**同样的参数**返回空图像。经 512 组形状 / 精度 / 插值模式组合验证，对合法输入数值零影响。

> <sub>Align zero-size semantics in <code>resize</code> / <code>rescale</code> with the warping ops. Verified numerically inert across 512 shape / dtype / interpolation combinations.</sub>

[**#4143**](https://github.com/kornia/kornia/pull/4143) — `kornia.core.__all__` 与 `kornia.color.__all__` 列出了模块里并未绑定的名字，`from kornia.core import *` 直接抛 `AttributeError`。既有的 API 面守卫看不到这类问题 —— 它比对的就是 `__all__` 本身，绑定丢失的名字仍然"在列"。恢复绑定、清理遗留条目，并加了一条覆盖全仓库 132 个声明 `__all__` 模块的解析守卫。

> <sub>`kornia.core.__all__` and `kornia.color.__all__` listed names that were not bound, so `import *` raised `AttributeError`. The existing surface guard could not see it — it compares `__all__` against itself. Restored the bindings, dropped the leftover entry, and added a resolve check across all 132 modules that declare `__all__`.</sub>

---

## 🛠 项目 · Projects

| 项目 | 说明 | 技术栈 |
|:--|:--|:--|
| [**mimo-tui**](https://github.com/hiyufan/mimo-tui) | AI 编码代理，5.7 MB 单二进制、零依赖<br><sub>支持 DeepSeek / MiMo / OpenAI / Claude</sub> | `Rust` |
| [**contest-ops**](https://github.com/hiyufan/contest-ops) | AI 驱动的竞赛管理平台 | `Go` `React` `Python` |
| [**aether-guide**](https://github.com/hiyufan/aether-guide) | 景区 AI 数字人智慧导览系统<br><sub>RAG 知识检索 · 多模态定位 (VPS / QR / 对话) · Live2D 数字人流式对话</sub> | `Python` `FastAPI` `Next.js` |
| [**campus-muse**](https://github.com/hiyufan/campus-muse) | 校园数字人导览系统<br><sub>GPS 地理围栏状态机 · STT→LLM→TTS 管线 · 语音问答闯关</sub> | `Python` `Vue` `Live2D` |
| **yf-quant** 🔒 | 基于 Qlib 的美股量化研究平台<br><sub>日频研究工作流：元数据存储、确定性校验、实验报告、Qlib 适配层</sub> | `Python` `Qlib` |
| [**bookloop**](https://github.com/hiyufan/bookloop) | 高校二手图书共享流转平台 | `Go` |
| [**edubridge**](https://github.com/hiyufan/edubridge) | 高校教务系统中间件 | `Go` `Vue` |

---

## 📚 正在学 · Currently Learning

<table>
<tr>
<td width="33%" valign="top">

**RAG · 检索增强生成**
<br><sub>分块与召回策略、重排序、评测方法</sub>

</td>
<td width="33%" valign="top">

**LLM 推理引擎**
<br><sub>vLLM / SGLang 的调度与显存管理</sub>

</td>
<td width="33%" valign="top">

**深度学习编译器**
<br><sub>TVM Relax、算子融合与代码生成</sub>

</td>
</tr>
</table>

---

## 📊 数据 · Stats

<div align="center">

<img src="https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username=hiyufan&theme=github" width="86%" />

<img height="170" src="https://github-profile-summary-cards.vercel.app/api/cards/repos-per-language?username=hiyufan&theme=github" />
<img height="170" src="https://github-profile-summary-cards.vercel.app/api/cards/most-commit-language?username=hiyufan&theme=github" />

<img height="170" src="https://streak-stats.demolab.com?user=hiyufan&hide_border=true&background=00000000&ring=4FC08D&fire=EE4C2C&currStreakLabel=4FC08D" />

</div>

### 🐍 贡献图 · Contribution Graph

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/hiyufan/hiyufan/output/github-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/hiyufan/hiyufan/output/github-snake.svg" />
  <img alt="contribution snake animation" src="https://raw.githubusercontent.com/hiyufan/hiyufan/output/github-snake.svg" />
</picture>

</div>


---

<div align="center">

### 📮 联系 · Contact

[![Email](https://img.shields.io/badge/yufan__ai@outlook.com-0078D4?style=flat-square&logo=microsoftoutlook&logoColor=white)](mailto:yufan_ai@outlook.com)
[![GitHub](https://img.shields.io/badge/@hiyufan-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/hiyufan)

<sub>欢迎交流 AI 基础设施、编译器与开源协作</sub><br>
<sub><i>Happy to talk about AI infrastructure, compilers, and open source.</i></sub>

</div>
