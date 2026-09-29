# Chinese-first Deep-Reading Scientific Reader contract

`paper_model.json` and `scientific_synthesis.json` represent canonical frozen scientific truth. `scripts/render_reader.py` produces the primary `reader/paper_reader.html`, `reader/paper_reader.md`, and PDF snapshot from a single unified Content IR (`reader/paper_reader_ir.json`).

## Physical Separation from Project Apply
The Paper Reader is strictly project-independent and immutable. Project Apply deltas are never merged into `reader/paper_reader.html`. Instead, explicit Apply requests generate separate reports under `apply/<project>/project_reader.html` and `.md`.

## Six-Chapter Scientific Narrative + Audit Appendix
1. **一分钟看懂这篇论文:** 研究问题、核心方法、核心发现、最大价值、最大风险与适用边界。
2. **论文到底在解决什么问题:** 研究背景、已有先验局限、切入视角、重要度定性。
3. **方法到底怎么工作:** 端到端流程、核心组件拆解、公式与假设；相关图表就地呈现。
4. **关键实验逐个说明:** 核心图表逐一精读（实验问题、观测结果、证明范围、盲区、异常信号）。
5. **证据最终支持了什么:** 最坚实证据链、最薄弱推理链、竞争解释、反常现象、适用边界。
6. **结论与边界:** 已建立的结论、证据边界和未决问题。
7. **证据审计附录:** 主张与 O/I/A 证据卡片列表、争议焦点、页面锚点、验证状态（次级可折叠）。

默认 `PAPER_READING` 不输出复用/迁移章节。论文技术细节提取通过显式 `PAPER_TECHNICAL_EXTRACTION` 意图请求；项目迁移只通过显式 Apply，且不改写冻结 Paper Reader。

Kami owns pixels, typography, page rasterization and PDF rendering; Evidentia owns scientific meaning and information architecture.

