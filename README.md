## Chen Yufan

Systems and AI infrastructure. Rust, Go, Python, TypeScript.

---

### Open source

Contributions to projects I use. Links go to the pull requests — some are still under review.

#### [Apache TVM](https://github.com/apache/tvm) · 13.7k ★ · deep learning compiler

[**#20245**](https://github.com/apache/tvm/pull/20245) — Validate `flatten` dims in the Relax PyTorch frontend. An out-of-range negative `start_dim` did not fail where it was used: it normalized to `-1`, folded an extra dimension into the product, and emitted a `reshape` to the wrong shape that only failed further downstream. Added the range and ordering checks, 0-d input support, and regression tests.

#### [Feast](https://github.com/feast-dev/feast) · 7.2k ★ · Linux Foundation AI & Data

[**#6801**](https://github.com/feast-dev/feast/pull/6801) — Fix an RBAC bypass ([GHSA-h543-6vgr-fm36](https://github.com/feast-dev/feast/security/advisories/GHSA-h543-6vgr-fm36)). Both token parsers granted a fully trusted internal identity from an *unverified* JWT decode, compared against a value hardcoded in Feast's own Helm chart — so any caller able to reach a server could forge it and skip every permission check on every project. Signed the internal token, moved the secret to a Kubernetes Secret with no default, and made an unset secret fail closed.

#### [kornia](https://github.com/kornia/kornia) · 11.3k ★ · differentiable computer vision

[**#4140**](https://github.com/kornia/kornia/pull/4140) — Align zero-size semantics in `resize` / `rescale`. They raised a bare `ZeroDivisionError` where `warp_affine`, `warp_perspective` and `center_crop` return an empty image for the same argument. Verified numerically inert across 512 shape / dtype / interpolation combinations.

---

### Projects

| | |
|---|---|
| [**mimo-tui**](https://github.com/hiyufan/mimo-tui) | AI coding agent in a 5.7 MB single binary, zero dependencies. DeepSeek, MiMo, OpenAI, Claude. `Rust` |
| [**MIRAX-API**](https://github.com/hiyufan/MIRAX-API) | AI API gateway / proxy. `Go` |
| [**ssgl**](https://github.com/hiyufan/ssgl) | AI-driven competition management platform. `Go` `React` `Python` |
| [**frbook**](https://github.com/hiyufan/frbook) | Campus second-hand book exchange platform. `Go` |
| [**jww.p**](https://github.com/hiyufan/jww.p) | Middleware for a university academic-affairs system. `Vue` |
