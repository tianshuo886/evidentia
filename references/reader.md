# Chinese-first Deep-Reading Scientific Reader contract

`paper_model.json` and `scientific_synthesis.json` represent canonical frozen scientific truth. `scripts/render_reader.py` produces the primary `reader/paper_reader.html`, `reader/paper_reader.md`, and PDF snapshot from a single unified Content IR (`reader/paper_reader_ir.json`).

## Physical Separation from Project Apply
The Paper Reader is strictly project-independent and immutable. Project Apply deltas are never merged into `reader/paper_reader.html`. Instead, explicit Apply requests generate separate reports under `apply/<project>/project_reader.html` and `.md`.

## Seven-Layer Scientific Hierarchy
1. **一分钟看懂这篇论文:** 研究问题、核心方法、核心发现、最大价值、最大风险与适用边界。
2. **论文到底在解决什么问题:** 研究背景、已有先验局限、切入视角、重要度定性。
3. **方法到底怎么工作:** 端到端流程、核心组件拆解、公式中文通俗解读与物理意义。
4. **关键实验逐个说明:** 核心图表逐一精读（对比内容、读图指引、证明范围、盲区、异常信号）。
5. **综合科学判断:** 最坚实证据链、最薄弱推理链、先验假设、竞争解释、反常现象、适用边界。
6. **可复用技术内容:** 可解耦算法组件、损失函数、预处理策略、落地迁移建议。
7. **证据审计附录:** 主张与 O/I/A 证据卡片列表、跨透镜争议焦点、页面锚点、验证状态（次级可折叠）。

Kami owns pixels, typography, page rasterization and PDF rendering; Evidentia owns scientific meaning and information architecture.

