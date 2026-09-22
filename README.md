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

> 给自己在用的项目提交的修复。链接指向 PR —— 11 个已提交，**5 个已合并**，1 个已批准；Apache TVM 占 9 个。
> <sub><i>Fixes sent to projects I use. Eleven pull requests: five merged, one approved; nine of them in Apache TVM.</i></sub>

### [Apache TVM](https://github.com/apache/tvm) &nbsp;`13.7k ★`&nbsp; 深度学习编译器

[**#20245**](https://github.com/apache/tvm/pull/20245) &nbsp;`🎉 已合并 merged`&nbsp; — 修复 Relax PyTorch 前端 `flatten` 的参数校验缺陷。越界的负 `start_dim` **不在使用处报错**：它被归一化成 `-1`，把多余的一维折进乘积，发出形状错误的 `reshape`，直到下游才失败。补上范围与顺序校验、0 维张量支持和回归测试。

> <sub>Validate `flatten` dims in the Relax PyTorch frontend. An out-of-range negative `start_dim` silently computed a wrong shape that only failed further downstream in `reshape`. Added range and ordering checks, 0-d input support, and regression tests.</sub>

[**#20254**](https://github.com/apache/tvm/pull/20254) &nbsp;`🎉 已合并 merged`&nbsp; — `torch.sort` / `torch.argsort` 返回 int64 索引，前端却发 int32。同文件的 `_topk` 已经显式覆盖了同一个 int32 默认值，说明这是遗漏而非约定；前端支持的其他索引类算子（`argmax`、`argmin`、`max(dim)`、`median(dim)`、`bucketize`）也都是 int64。一张导入图会因此对同一种值带上两种索引 dtype。

> <sub>`torch.sort` / `torch.argsort` return int64 indices; the frontend emitted int32. `_topk` in the same file already overrides the identical default, and every other index-producing op comes out int64 — so one imported graph could carry two index dtypes for the same kind of value.</sub>

[**#20255**](https://github.com/apache/tvm/pull/20255) &nbsp;`🎉 已合并 merged`&nbsp; — Relax 的 `reshape` 把目标形状里的字面 `0` 读作"沿用输入对应维度"（ONNX `allowzero=0` 语义），PyTorch 读作真实的零维。空张量上的 `reshape` / `view` / `flatten` / `unflatten` 因此报错或**静默给出错误形状**；`flatten` 在 `(0,3)` 上恰好正确，正是这个巧合掩盖了其余情形。与 torch 逐例对照验证：2132 组静态形状，以及 938 组目标可含符号维的动态形状 —— 后者由维护者 review 中指出的两个残留缺口驱动补上，修复后其中 314 组由错转对。顺带修掉 `RemoveRedundantReshape` 的一个同源缺陷：它合并相邻 reshape 时把已解析的字面 `0` 挪到新输入上，零被重新当成"拷贝维度"，**整段改写连同 reshape 一起被删掉**（938 组里有 24 组因此出错）。

> <sub>Relax's `reshape` reads a literal `0` as "copy the input dimension" (ONNX `allowzero=0`) where PyTorch reads a real zero-sized one, so `reshape` / `view` / `flatten` / `unflatten` on empty tensors raised or silently produced a wrong shape. Verified case by case against torch: 2132 static shapes, plus 938 dynamic ones whose target can reach a symbolic dimension, which found two further gaps under review. Also fixes the same confusion in <code>RemoveRedundantReshape</code>, which re-parented a resolved target onto a different input and so read its literal zeros as dimension copies, dropping the rewrite entirely in 24 of those cases.</sub>

**2026-09 差分扫描批次** · 用 88 个算子 × 7 种输入形状对照 `torch.export`，一次找出六处；每个 PR 都带修前/修后逐例对照、回归测试在旧 head 上确认失败。
<sub><i>A differential-sweep batch: 88 ops × 7 input shapes against `torch.export`, six findings; each PR carries a per-case before/after diff and a regression test shown failing on the previous head.</i></sub>

[**#20377**](https://github.com/apache/tvm/pull/20377) &nbsp;`✅ 已批准 approved`&nbsp; — `reshape` 的恒等跳过用 `list ==` 比较形状，符号维上 `==` 返回的是 `PrimExpr` 而不是布尔值，同秩目标直接抛 `ValueError`。改为逐维比较，938 组动态形状中 40 组由抛错转为正确。
> <sub>The identity-reshape shortcut compared shapes with `list ==`; on a symbolic dim `==` yields a `PrimExpr`, so any same-rank target raised. Dimension-wise comparison instead; 40 of 938 dynamic cases go from raising to correct.</sub>

[**#20372**](https://github.com/apache/tvm/pull/20372) &nbsp;`🔄 review 中`&nbsp; — Python 标量参与二元运算时被**向下转成张量的 dtype**：`int_tensor * 0.5` 静默算成 `x * 0`，`x < 1.5` 变成 `x < 1`。改用 `torch.result_type` 决定提升方向。864 组（18 算子 × 8 dtype × 6 标量，LLVM 真跑比值）中 168 组由错转对，0 回归。
> <sub>A Python scalar was truncated to the tensor's dtype, so `int_tensor * 0.5` silently became `x * 0`. Promotion now follows `torch.result_type`; 168 of 864 numerically-checked cases repaired, none regressed.</sub>

[**#20373**](https://github.com/apache/tvm/pull/20373) &nbsp;`🔄 review 中`&nbsp; — 除法家族：`int / int` 应为 float32 却整除；`x // 2` 对任何 float 张量抛 `TypeError`（标量常量不带 dtype）；`2 / x` 经 `reciprocal` 同样整除且两个 translator 各抄一份。统一到真除法规则；上一批剩余的 52 处数值错误清零。
> <sub>Division family: `int / int` was an integer quotient, `x // 2` raised on every float tensor, `2 / x` via `reciprocal` was duplicated and wrong. One true-division rule; the remaining 52 wrong-value cases drop to zero.</sub>

[**#20374**](https://github.com/apache/tvm/pull/20374) &nbsp;`🔄 review 中`&nbsp; — `cumsum` / `cumprod` 对整型和 bool 输入保持输入 dtype，torch 用 int64 累加：`uint8 [200, 100, 50]` 的前缀和变成 `[200, 44, 94]`。45 组溢出输入全部对齐。
> <sub>`cumsum` / `cumprod` kept the input dtype where torch accumulates in int64, so a uint8 running sum wrapped. All 45 overflow-prone cases now match.</sub>

[**#20375**](https://github.com/apache/tvm/pull/20375) &nbsp;`🔄 review 中`&nbsp; — 补上 `amax` / `amin` / `min.dim` 三个缺失的转换器（`logsumexp` 的分解也经过 `amax`），`_max_dim` 泛化为一个 `largest` 参数服务两端。
> <sub>Adds the missing `amax` / `amin` / `min.dim` converters (`logsumexp` decomposes through `amax`); `_max_dim` generalised to serve both ends.</sub>

[**#20376**](https://github.com/apache/tvm/pull/20376) &nbsp;`🔄 review 中`&nbsp; — `any` 对非 bool 输入返回的是**最大值**而不是真值（`[0, 0, 5].any(1)` 给 `5`），`any.default` 与 `prod.dim_int` 缺转换器，`prod` 对整型不做 int64 累加。四处一并修正。
> <sub>`any` on a non-bool input returned the maximum instead of a truth value; `any.default` and `prod.dim_int` had no converter; `prod` skipped int64 accumulation. All four fixed together.</sub>

### [kornia](https://github.com/kornia/kornia) &nbsp;`11.3k ★`&nbsp; 可微分计算机视觉

[**#4140**](https://github.com/kornia/kornia/pull/4140) &nbsp;`🎉 已合并 merged`&nbsp; — 统一 `resize` / `rescale` 的零尺寸语义。它们对零尺寸输出抛裸 `ZeroDivisionError`，而 `warp_affine`、`warp_perspective`、`center_crop` 对**同样的参数**返回空图像。空结果还需保持在自动微分图上 —— 否则一个退化成零尺寸的 batch 元素会静默断开梯度，这是 review 中提出、复现并修掉的。经 512 组形状 / 精度 / 插值模式组合验证，对合法输入数值零影响。

> <sub>Align zero-size semantics in <code>resize</code> / <code>rescale</code> with the warping ops, and keep the empty result attached to the autograd graph so a batch element that degenerates to a zero-sized output still contributes a zero gradient. Verified numerically inert across 512 shape / dtype / interpolation combinations.</sub>

[**#4143**](https://github.com/kornia/kornia/pull/4143) &nbsp;`🎉 已合并 merged`&nbsp; — `kornia.core.__all__` 与 `kornia.color.__all__` 列出了模块里并未绑定的名字，`from kornia.core import *` 直接抛 `AttributeError`。既有的 API 面守卫看不到这类问题 —— 它比对的就是 `__all__` 本身，绑定丢失的名字仍然"在列"。恢复绑定、清理遗留条目，并加了一条覆盖全仓库每一个声明 `__all__` 模块的解析守卫。

> <sub>`kornia.core.__all__` and `kornia.color.__all__` listed names that were not bound, so `import *` raised `AttributeError`. The existing surface guard could not see it — it compares `__all__` against itself. Restored the bindings, dropped the leftover entry, and added a resolve check across every module that declares `__all__`.</sub>

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
