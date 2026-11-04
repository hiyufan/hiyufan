<div align="center">

# Hi there, I'm Yufan 👋

<a href="https://github.com/hiyufan">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=20&duration=3000&pause=1000&color=4FC08D&center=true&vCenter=true&width=560&lines=Systems+%26+AI+Infrastructure;Patching+deep+learning+compiler+frontends;Building+fast+tools+in+Rust;Contributor+to+Apache+TVM+%26+kornia" alt="Typing SVG" />
</a>

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

## 🙋 About Me

I work on systems and ML infrastructure — compilers, runtimes, and the tooling around them. I like bugs that don't crash: the ones that quietly hand you the wrong shape three ops later.

- 🔭 Currently sending correctness fixes to **[Apache TVM](https://github.com/apache/tvm)** and **[kornia](https://github.com/kornia/kornia)**
- 🦀 Building **[alcedo](https://github.com/hiyufan/alcedo)**, a pure-Rust video parsing core for 35 platforms
- 🌱 Learning LLM inference engines, RAG, and deep learning compilers (more below)
- 💬 Ask me about PyTorch → TVM Relax import, shape semantics, or why your `reshape` is lying to you
- 📫 Reach me at **[hi@oiya.net](mailto:hi@oiya.net)**

---

## 🔧 Open Source Contributions

> Fixes I sent upstream to projects I actually use — **5 PRs, all merged**.

### <img src="https://github.com/apache.png" width="20" align="center" /> [Apache TVM](https://github.com/apache/tvm) &nbsp;![stars](https://img.shields.io/github/stars/apache/tvm?style=flat-square&label=%E2%98%85&color=425066)

| PR | Status | What it fixes |
|:--|:--|:--|
| [**#20255**](https://github.com/apache/tvm/pull/20255) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | Relax `reshape` read a literal `0` as "copy this dim" (ONNX semantics) where PyTorch means a real zero-sized dim, so empty-tensor `reshape` / `view` / `flatten` / `unflatten` raised or **silently returned the wrong shape**. Verified against torch on 2,132 static + 938 dynamic shapes, and fixed the same bug hiding in `RemoveRedundantReshape`. |
| [**#20254**](https://github.com/apache/tvm/pull/20254) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | `torch.sort` / `argsort` emitted int32 indices while every other index op was int64 — one graph, two index dtypes. |
| [**#20245**](https://github.com/apache/tvm/pull/20245) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | `flatten` didn't validate dims, so a bad negative `start_dim` produced a broken `reshape` downstream instead of failing at the call site. |

### <img src="https://github.com/kornia.png" width="20" align="center" /> [kornia](https://github.com/kornia/kornia) &nbsp;![stars](https://img.shields.io/github/stars/kornia/kornia?style=flat-square&label=%E2%98%85&color=5C3EE8)

| PR | Status | What it fixes |
|:--|:--|:--|
| [**#4140**](https://github.com/kornia/kornia/pull/4140) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | Zero-size `resize` / `rescale` threw `ZeroDivisionError` where the warping ops return an empty image. Now matches them, and keeps the result on the autograd graph. Verified inert on 512 shape / dtype / mode combos. |
| [**#4143**](https://github.com/kornia/kornia/pull/4143) | ![merged](https://img.shields.io/badge/merged-8957E5?style=flat-square&logo=github&logoColor=white) | `__all__` listed unbound names, so `from kornia.core import *` crashed. Restored them and added a repo-wide check that every exported name resolves. |

---

## 🚀 Featured Projects

| Project | Description | Stack |
|:--|:--|:--|
| 🦀 [**alcedo**](https://github.com/hiyufan/alcedo) | High-performance video parsing core for 35 platforms — pure Rust, zero external processes<br><sub>YouTube · TikTok · Douyin · Bilibili · Xiaohongshu · Kuaishou · …</sub> | `Rust` |
| 🎞️ [**ynvan.com**](https://ynvan.com) | Grab videos and images from Douyin, Xiaohongshu, X and more; one-click GIF and Live Photo export<br><sub>Live service, powered by parse-video-py</sub> | `Python` `FastAPI` `Docker` |
| 📈 **yf-quant** 🔒 | US equities quant research platform built on Qlib<br><sub>Daily-frequency workflows, metadata store, deterministic checks, experiment reports</sub> | `Python` `Qlib` |
| 🎓 [**edubridge**](https://github.com/hiyufan/edubridge) | Middleware for university academic systems | `Go` `Vue` |

---

## 📚 Currently Learning

<table>
<tr>
<td width="33%" valign="top">

**🔍 RAG**
<br><sub>Chunking & retrieval strategies, reranking, evaluation</sub>

</td>
<td width="33%" valign="top">

**⚡ LLM Inference Engines**
<br><sub>Scheduling & KV-cache memory management in vLLM / SGLang</sub>

</td>
<td width="33%" valign="top">

**🧠 DL Compilers**
<br><sub>TVM Relax, operator fusion, code generation</sub>

</td>
</tr>
</table>

---

## 📊 GitHub Stats

<div align="center">

<img src="https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username=hiyufan&theme=github" width="86%" />

<img height="170" src="https://github-profile-summary-cards.vercel.app/api/cards/repos-per-language?username=hiyufan&theme=github" />
<img height="170" src="https://github-profile-summary-cards.vercel.app/api/cards/most-commit-language?username=hiyufan&theme=github" />

<img height="170" src="https://streak-stats.demolab.com?user=hiyufan&hide_border=true&background=00000000&ring=4FC08D&fire=EE4C2C&currStreakLabel=4FC08D" />

</div>

### 🐍 Contribution Graph

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/hiyufan/hiyufan/output/github-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/hiyufan/hiyufan/output/github-snake.svg" />
  <img alt="contribution snake animation" src="https://raw.githubusercontent.com/hiyufan/hiyufan/output/github-snake.svg" />
</picture>

</div>

---

<div align="center">

### 🤝 Let's Connect

[![Email](https://img.shields.io/badge/hi@oiya.net-0078D4?style=flat-square&logo=gmail&logoColor=white)](mailto:hi@oiya.net)
[![GitHub](https://img.shields.io/badge/@hiyufan-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/hiyufan)

<sub>Always happy to chat about AI infra, compilers, and open source. ⭐ Thanks for stopping by!</sub>

</div>
