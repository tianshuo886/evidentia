# Chinese-first Deep-Reading Scientific Reader contract

`paper_model.json` and `scientific_synthesis.json` represent canonical frozen scientific truth. `scripts/render_reader.py` produces the primary `reader/paper_reader.html`, `reader/paper_reader.md`, and PDF snapshot from a single unified Content IR (`reader/paper_reader_ir.json`).

## Physical Separation from Project Apply
The Paper Reader is strictly project-independent and immutable. Project Apply deltas are never merged into `reader/paper_reader.html`. Instead, explicit Apply requests generate separate reports under `apply/<project>/project_reader.html` and `.md`.

## Paper-specific Story Spine + quiet provenance appendix
The manuscript is composed from the paper's reconstructed argument. Section count, titles, and order follow the paper's question, method, decisive results, assessment, and boundaries; they are not a fixed six-chapter template. Every section is Chinese-first prose with local evidence links and figures placed where the argument needs them.

The final section records what the evidence establishes and what remains open. A quiet provenance appendix links to the separate Evidence Atlas for claim-level inspection; audit roles and O/I/A cards never appear in the human narrative.

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
