### Hey, I'm Yufan 👋

I work on systems and ML infrastructure — compilers, runtimes, and the tooling around them. Most of my open source time goes into fixing correctness bugs in deep learning compiler frontends; the rest goes into fast, dependency-free tools in Rust.

- 🔭 Digging into **LLM inference engines** — scheduling and KV-cache memory management in vLLM and SGLang
- 🌱 Learning **RAG** properly: chunking, retrieval, reranking, and how to evaluate any of it
- 🧩 Contributing to **Apache TVM** (Relax) and **kornia**
- 📫 [hi@oiya.net](mailto:hi@oiya.net)

**Languages:** Rust · Go · Python · TypeScript &nbsp;|&nbsp; **Tools:** PyTorch · Apache TVM · React · Vue · Docker · Linux

---

#### Open source

All merged.

**[Apache TVM](https://github.com/apache/tvm)** — deep learning compiler

- [#20255](https://github.com/apache/tvm/pull/20255) — Relax `reshape` read a literal `0` as "copy this dim" where PyTorch means a real zero-sized dim, so ops on empty tensors raised or silently returned the wrong shape. Checked against torch on 3,000+ static and dynamic shapes; also fixed the same bug hiding in `RemoveRedundantReshape`.
- [#20254](https://github.com/apache/tvm/pull/20254) — `torch.sort` / `argsort` now emit int64 indices like every other index op, instead of mixing two index dtypes in one graph.
- [#20245](https://github.com/apache/tvm/pull/20245) — `flatten` validates its dims, so a bad negative `start_dim` fails at the call site rather than as a broken `reshape` downstream.

**[kornia](https://github.com/kornia/kornia)** — differentiable computer vision

- [#4140](https://github.com/kornia/kornia/pull/4140) — Zero-size `resize` / `rescale` return an empty tensor that stays on the autograd graph, matching the warping ops, instead of throwing `ZeroDivisionError`.
- [#4143](https://github.com/kornia/kornia/pull/4143) — Fixed `__all__` entries that broke `import *`, and added a repo-wide check that every exported name actually resolves.

#### Projects

- **[alcedo](https://github.com/hiyufan/alcedo)** — Video parsing core for 35 platforms (YouTube, TikTok, Douyin, Bilibili, …). Pure Rust, no external processes. `Rust`
- **[ynvan.com](https://ynvan.com)** — Pull videos and images from Douyin, Xiaohongshu, X and more; one-click GIF and Live Photo export. `Python` `FastAPI` `Docker`
- **[edubridge](https://github.com/hiyufan/edubridge)** — Middleware for university academic systems. `Go` `Vue`
- **yf-quant** *(private)* — US equities research platform on Qlib: daily-frequency workflows, deterministic checks, experiment reports. `Python`

---

<sub>Always happy to talk compilers, ML infra, or open source — just send an email.</sub>
