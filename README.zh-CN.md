# Evidentia

[English](README.md) · [中文](README.zh-CN.md)

## 基于真实证据的论文深度研究操作系统 (Paper Research OS)

Evidentia 是一个面向单篇学术论文的严密科研操作系统。它将用户提供的论文 PDF 转化为具备全链路证据锚定、高度可审计、可长期存证的研究对象：通过“多模态物理源重构”抓取图表公式与排版信息，经“Lead Reader”梳理原生论证拓扑，由“4 大通用核心 + 2 项自适应专项 Lens”展开严格语境隔离的深度重读，通过“编辑部修订备忘录（Revision Memo）”提炼学术张力与修订指令，基于论文独有的思想脉络生成“动态反模板大纲（Narrative Plan）”，由强模型“Lead Writer”撰写出版级中文学术精读手稿，并通过“Kami 排版引擎”完成现代学术阅读器（HTML/Markdown/矢量 PDF）及审计级“Evidence Atlas 证据图谱”的渲染呈现。

本项目仅包含可复用的通用科研 Skill 与测试 Harness，已在多篇真实顶级经同行评审论文上完成正式基准测试与验证。

---

## 为什么需要 Evidentia？

传统大模型对学术论文的泛读与总结存在根本性的“学术失真”：

- **证据蒸发：** 核心图表与数据表格被粗暴压缩为几句笼统概括，原始实证链条彻底遗失；
- **盲从作者修辞：** 模型倾向于全盘接受论文作者的主观宣称，无法主动发掘未言明的先决假设、薄弱的对照实验或潜在的替代解释；
- **模板套用偏见：** 机械套用千篇一律的 IMRaD（背景-方法-实验-结论）八股结构，严重歪曲了数学定理推导、物理精密测量、综述分类或观察证伪类论文的内在论证逻辑；
- **过早引入项目偏见：** 在首次精读时过早注入研究人员的项目需求，导致模型迎合预期，将论文读成“支持当前构想”的素材；
- **认知模糊与幻觉：** 将实验中的异常反常点、统计不确定性与未决争议抹平为平滑但不可靠的陈述。

Evidentia 确立了三项不可动摇的顶层公理：

> **Paper decides the story.（论文决定论证结构）**  
> **Evidentia enforces rigor.（系统保障科学严密）**  
> **Kami presents the story.（排版专注视觉呈现）**

---

## 权威规范架构 (Canonical Reader v3)

```text
原始论文 PDF (paper.pdf)
   ↓
页面先行多模态视觉重构（全文文本 + 高清页面栅格化 + 确定性资产裁剪，绑定 source_sha256）
   ↓
确定性源锁定与语义视觉核验（apply_visual_verification.py）
   ↓
Lead Reader 主读通行（强模型：论文全局定性、开放论证拓扑、自适应专项透镜规划）
   ↓
4 大通用核心 + 2 项自适应专项 Lens 重读（严格执行上下文边界隔离，严禁兄弟透镜串供与多数票表决）
   ↓
学术修订备忘录 (Revision Memo)（结构化修订指令：ADD, REWRITE, CORRECT, QUALIFY；严谨保留未决张力）
   ↓
动态叙事大纲 (Dynamic Narrative Plan)（依论文内在逻辑定制章节拓扑，彻底消除八股模板偏见）
   ↓
Lead Writer 手稿撰写（强模型：严格遵循 narrative_manuscript 规范，产出出版级中文学术精读手稿）
   ↓
完整性与抗模板门禁审计（资产完整性闭环校验、引文页码锚定、章节结构多样性核验）
   ↓
Kami 呈现转换层（纯视觉渲染：版面空间律动、字体排印、自适应 HTML、矢量打印 PDF）
   ↓
交付成果：交互式学术阅读器 (HTML + Markdown + Print PDF) 与次级审计图谱 (Evidence Atlas)
   ↓
PAPER_COMPLETE（标准精读流程在此严格终结，冻结论文认知）

[当且仅当用户显式发起请求时]
   ↓
上下文关联项目迁移研报 (/evidentia-apply) → 物理隔离的项目研报与 Research Delta (apply/<project>/)
   ↓
长期科研记忆积累 (/evidentia-memory)
```

---

## Issue #19 真实论文正式基准测试验证 (Release Benchmark)

Evidentia Reader v3 科学架构已在提交 `4139ca7b0b1ae72c0930801df5e50653b59a7e92` 完成正式冻结，并在 **GitHub Issue #19** 下以 `antigravity/gemini-3.8-flash [magpie]` 作为官方指定科学模型，对 6 篇横跨不同学科结构的真实顶级论文完成双盲镜像 A/B 评测：

1. `BENCH-01`: *Attention Is All You Need* (经典架构与序列建模工程)
2. `BENCH-02`: *LoRA: Low-Rank Adaptation of Large Language Models* (参数高效微调与系统服务)
3. `BENCH-03`: *A high-resolution canopy height model of the Earth* (全球遥感观测与时空概率反演)
4. `BENCH-04`: *Highly accurate protein structure prediction with AlphaFold* (空间图变换与生物计算)
5. `BENCH-05`: *Quantum supremacy using a programmable superconducting processor* (超导量子基质精密计量与外推)
6. `UNSEEN-01`: *Understanding deep learning requires rethinking generalization* (**架构冻结后遴选之盲测论文**：数学构造定理与随机化反事实证伪)

**测试评测结论：** **`ISSUE19_RELEASE_GATE = PASS`**
- **核心维度零退步：** 叙事清晰度、完备性、方法阐释三大核心维度在全部 18 场评测中取得 **0 负**（全面超越或持平原生顶级 Gemini 直读强基线）；
- **盲测论文抗模板验证：** 对未见论文 UNSEEN-01，自发梳理出其独有的“悖论 $\to$ 经验证伪 $\to$ 构造定理 $\to$ 经典范式破产 $\to$ 隐式正则化前沿”6 章节拓扑，零模板套用；
- **压倒性增值体现：** 图表公式精准解析 (DIM-05) 与证据追溯可审计性 (DIM-11) 取得 **6/6 全胜**；
- 详见完整基准报告：[`ISSUE19_FORMAL_AB_BENCHMARK_REPORT.md`](ISSUE19_FORMAL_AB_BENCHMARK_REPORT.md)。

---

## 核心设计规范

1. **客观精读优先，迁移必须显式隔离：**
   默认意图始终为 `PAPER_READING`。在论文精读阶段，项目材料、代码库与研究记忆完全物理隐身，杜绝先入为主。项目迁移仅能通过显式 `/evidentia-apply` 触发，且绝不改写已冻结的论文事实。
2. **4 大通用核心 + 2 项自适应专项 Lens：**
   - **Argument & Narrative (论证与叙事):** 论文如何建立核心主张，如何组织证据链；
   - **Method & Study Design (方法与研究设计):** 数学建模、算法逻辑与实验流程剖析；
   - **Evidence & Results (实证与结果):** 关键量化数据、消融对照与证据力度；
   - **Validity & Boundary (效度与边界):** 潜在脆弱假设、反事实解释与认识论局限。
   根据论文类型，自动选配 2 项专项透镜（如机制与因果、代码可复现性、数理证明完整性、测量保真度等）。
3. **严格上下文隔离与密码学凭证：**
   每个 Lens 独立在专属的文件系统输入快照（`provenance/lens/<task_id>`）中运行，输出绑有密码学凭证与源码/提示词哈希，杜绝串供。
4. **编辑部备忘录取代多数票表决：**
   设立类似学术期刊编辑的 Revision Memo 机制，对各视角发现给出“保留、扩充、更正、校准、边界限定”等具体指令，坚决保留真实的学术争议与反常数据点。
5. **Kami 排版专用边界：**
   Kami 专注于现代学术排版、字距行高、图表自适应排版及高保真 PDF 导出；Kami 严禁裁决学术观点、重排论证逻辑、或为迎合排版擅自增删科学内容。

---

## 常用命令

### 1. 深度精读一篇论文

```bash
# 基于本地 PDF 进行端到端权威精读：
python scripts/evidentia.py run --pdf /path/to/paper.pdf --out workspace/

# 基于 DOI 或 arXiv ID 自动获取并精读：
python scripts/evidentia.py run --doi 10.48550/arXiv.2106.09685 --out workspace/
```

### 2. 状态查询与任务提交

```bash
# 查看工作空间 Reader v3 阶段状态：
python scripts/evidentia.py status --out workspace/

# 获取下一项待执行任务数据包：
python scripts/evidentia.py next --out workspace/

# 提交 Agent 执行结果进入可信网关：
python scripts/evidentia.py submit --out workspace/ --task TASK-V3-LEAD-READING --result result.json
```

### 3. 项目落地迁移研报（仅显式需要时）

```bash
python scripts/pipeline.py apply --paper workspace/ --project my_project.md
python scripts/validate_delta.py --paper workspace/ --delta workspace/apply/my_project/research_delta.json
```

---

## 开源协议

Apache License 2.0。详见 [LICENSE](LICENSE)。
