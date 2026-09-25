# Evidentia

## 基于证据的论文研究操作系统

Evidentia 是一个面向单篇论文的深度研究 Skill。它把用户提供的 PDF 转化为一个可长期保存、可追溯、可复核的研究对象：先重建论文的证据来源层，再进行六个独立视角的重读，冻结论文事实，生成统一 Reader，并在需要时把论文投射到一个具体项目中，形成带证据来源的 Research Delta。

这个仓库只保存可复用的 Skill，不包含任何特定论文、实验文章或项目材料。

## 它解决什么问题

普通论文总结经常丢掉真正影响研究决策的内容：

- 图表被压缩成文字，原始证据消失；
- 结论没有和 Figure、Table、Experiment 建立稳定绑定；
- AI 顺着作者叙事复述，没有主动检查薄弱证据、替代解释和失败条件；
- 项目目标过早进入阅读，导致论文被读成“支持当前计划”的材料；
- 过一段时间后只能翻聊天记录，无法快速恢复论文判断；
- 固定模板诱导章节复述，容易漏掉异常、负结果和可复用技术构件。

Evidentia 用 Paper Model、Evidence Graph、Source Reconstruction、六 Lens、Frozen Model、Unified Reader 和 Research Delta 解决这些问题。

## 系统架构

```text
paper.pdf
   ↓
只包含论文的隔离工作区 + Figure/Table 重建
   ↓
Paper Model + Evidence Graph
   ↓
Author / Reviewer / Mechanism / Builder / Anomaly / Counterfactual
   ↓
冻结 + SHA-256 完整性门禁
   ↓
Paper Reader（HTML 主阅读，PDF 快照）
   ↓
可选的项目 contextual apply
   ↓
Research Delta + Project Gap Map + literature index
```

Paper Model 是事实层。Reader、Kami 兼容展示和项目分析都只能作为下游适配层，不能反过来改变论文结构或论文事实。

## 安装

### 环境要求

- Python 3.10+
- PyMuPDF
- jsonschema
- Jinja2
- WeasyPrint（用于生成 PDF 快照，可选；HTML 不依赖它）

### 安装命令

```bash
git clone https://github.com/tianshuo886/paper-read.git
cd paper-read
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

## 基本使用

### 1. 开始一次隔离的论文阅读

```bash
python scripts/pipeline.py read \\
  --pdf /path/to/paper.pdf \\
  --out /path/to/paper-output
```

带补充材料：

```bash
python scripts/pipeline.py read \\
  --pdf paper.pdf \\
  --supplement supplement.pdf \\
  --out paper-output
```

这一步会创建 `working/` 隔离工作区、复制 PDF、提取 Figure/Table inventory、建立 source map。它不会加载项目资料。

### 2. 创建六个独立 Lens 任务包

```bash
python scripts/lens_runner.py --out paper-output
```

六个 Lens 必须分别针对论文 PDF 和冻结前的 base understanding 执行，并分别写入：

```text
lens/author.json
lens/reviewer.json
lens/mechanism.json
lens/builder.json
lens/anomaly.json
lens/counterfactual.json
```

一次“多视角综合总结”不能替代六个独立 pass。

### 3. 验证并冻结

```bash
python scripts/check_lenses.py --out paper-output
python scripts/merge_lenses.py --out paper-output
python scripts/build_graph.py --out paper-output
python scripts/validate_model.py --out paper-output
python scripts/freeze_check.py --out paper-output
```

如果存在缺失 Lens、悬空 ID、未检查 Figure/Table、关键图文件缺失、覆盖审计缺失或没有证据的 Claim，冻结会失败。

### 4. 生成和审计 Reader

```bash
python scripts/render_reader.py --out paper-output
python scripts/reader_audit.py --out paper-output
```

Reader 包含三个阅读层级：30 秒 Dashboard、5 分钟 Paper Map/Claim Cards、30–60 分钟 Evidence Atlas。HTML 是主阅读界面，PDF 是存档快照。

### 5. 将冻结论文投射到项目

```bash
python scripts/pipeline.py apply \\
  --paper paper-output \\
  --project /path/to/project.md \\
  --focus "水汽通道重建"
```

Apply 会先验证 Frozen Model 的哈希，再把一个项目文档复制到 `apply/<project>/`。之后在这个独立目录完成 contextual reread，填写 `project_context.json` 和 `research_delta.json`：

```bash
python scripts/validate_delta.py \\
  --paper paper-output \\
  --delta paper-output/apply/project/research_delta.json
```

Research Delta 可以记录改变的判断、新证据、新未知、可迁移构件、被否定或降级的计划、新实验，也可以明确输出 `NO_NEW_ACTIONABLE_EXPERIMENT`。

## 核心数据对象

| 对象 | 作用 |
|---|---|
| `paper_model.json` | 论文事实、判断和 epistemic state 的规范层 |
| `evidence_graph.json` | Claim、Observation、Figure、Table、Experiment 的类型化关系 |
| `source_map.json` | 页码、章节、公式和文中引用的 provenance |
| `lens/*.json` | 六个独立 Lens 的重读结果 |
| `manifest.json` | Frozen 状态和 SHA-256 哈希 |
| `reader/reader.html` | 人类实际阅读的主界面 |
| `research_delta.json` | 与具体项目有关的变化，和论文事实分离保存 |
| `literature_index.json` | 跨论文长期记忆的基础索引 |

## 设计原则

- **先 Open Reading，再项目投射：** 项目只能改变后续关注点，不能改变论文事实。
- **先恢复论文自然结构，再填 Schema：** 防止模板把论文读成填空题。
- **Figure-first：** 所有 Figure 和 Table 都必须进入 inventory 并被检查。
- **Observation / Interpretation / Assessment 分离：** 数据、作者解释、读者判断不能混写。
- **六 Lens 独立执行：** 不能用一次综合 Prompt 冒充六次重读。
- **先 Freeze，再 Apply：** 项目分析不能静默修改论文事实。
- **Kami 只负责展示：** 展示模板不能决定论文的信息架构。
- **不确定性可见：** unresolved、insufficient evidence 等状态必须保留。

## 使用场景

- 在复现或迁移一个方法前，完整检查论文的证据链。
- 判断论文最重要的 Claim 是否真的被 Figure、Table 和 Experiment 支持。
- 从论文中提取可迁移的 loss、diagnostic、ablation、采样策略和 failure mode。
- 将论文证据和项目已有研究缺口进行映射。
- 判断一个实验计划应该直接迁移、适配、仅作启发、拒绝、降级或删除。
- 建立不依赖聊天记录的长期论文研究记忆。

## 隔离与安全

Open Reading 只能接收论文 bundle 和 Skill 资源。项目仓库、项目计划、聊天记录、记忆和连接器数据都不属于它的输入边界。Apply 是单独阶段，只有 Frozen Model 通过哈希校验后才能开始。

## 测试

```bash
pytest -q
```

测试包含悬空 evidence、缺失 Lens、关键图文件缺失和 Frozen Model 被篡改等失败用例。

## 命名

仓库 URL 暂时保留 `paper-read`，以保证已有链接稳定。Skill 正式名称是 **Evidentia**，完整描述是 **Evidence-Grounded Paper Research OS**。
