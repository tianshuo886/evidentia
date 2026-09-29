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

## Faithful-reading Firewall & Intent Invariants

> **永久设计原则：First understand the paper on its own terms. Only transfer it when the user asks. Relevance is not permission.**

### 四大显式意图
1. **PAPER_READING (默认)**:
   只回答：“论文到底说了什么、做了什么、展示了什么、确立了什么？”
   严禁推测用户项目迁移意图；严禁出现“可复用技术内容”或“迁移到你的项目”章节。
2. **PAPER_TECHNICAL_EXTRACTION (显式技术提取)**:
   当用户明确要求“提取可复现细节/算法/组件”时生成，严格限于论文技术范畴，输出 `reader/technical_extraction.md` 和 `.html`，不涉及用户项目。
3. **PROJECT_APPLY (显式项目适配)**:
   仅在用户明确发出 `/evidentia-apply` 或“结合我的项目”请求时触发，输出位于 `apply/<project>/`，绝对不改写已冻结的 Paper Reader。
4. **MEMORY_OPERATION (显式记忆操作)**:
   仅在用户明确管理或检索研究记忆时触发。

### 输入防火墙 (Input Firewall)
在 `PAPER_READING` 与 `PAPER_TECHNICAL_EXTRACTION` 阶段，工作区与任务输入严格禁止访问 `apply/**`、项目文档与项目记忆。

Kami owns pixels, typography, page rasterization and PDF rendering; Evidentia owns scientific meaning and information architecture.

