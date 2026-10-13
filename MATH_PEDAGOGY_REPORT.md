# Mathematical Formula Pedagogy & Teaching Contract Report (Issue #40)

**Date**: 2026-10-13  
**Status**: PASSED / VERIFIED  
**Target Issue**: GitHub Issue #40: P0: Formula Pedagogy — Explain the mathematics, not just typeset it  
**Dependency**: Issue #39 (Mathematical Formula Source Fidelity)

---

## 1. Problem Statement & Observed Deficiencies

In the baseline Oct 13 reader run, mathematical equations suffered from severe comprehension issues:
1. **Generic Single-Sentence Labels**: Formula blocks were rendered with generic one-line headers (e.g., `"Critic 多维结构化打分公式"`, `"Main Agent 基于诊断…更新…"`) with zero pedagogical decomposition of the constituent variables, terms, or units.
2. **Collapsed ASCII Variables**: Prose used shorthand abbreviations (e.g. $Score_t, C_t, B_t$) without defining their domains, dimensions, or operational rationale.
3. **Missing Intuition & Operators**: Readers could not deduce *why* terms were structured as they were—such as why $1 - B_t$ was used instead of $B_t$, why $\frac{\Delta\text{Acc}}{\Delta t}$ was computed instead of absolute gain, or why $\exp(-\sigma \|\nabla_\theta^2\|)$ acted as an exponential penalty.
4. **Undisclosed Engineering Surrogates**: The paper relied on practical proxies (such as using the coefficient of variation of the last 50 losses, $\text{CV}_{50}$, as a lightweight surrogate for the computationally prohibitive second-order Hessian $\nabla_\theta^2$), but previous readers failed to explain this gap or acknowledge unstated hyperparameters ($\alpha, \beta, \sigma$).

---

## 2. Pedagogical Architecture & Implementation Contract

To satisfy Issue #40, we established a strict **Teaching Contract** across the entire pipeline:

### 2.1 Structured Pedagogy Schemas
Updated `schemas/equation.schema.json` and `schemas/narrative_manuscript.schema.json` to define typed pedagogy properties:
- `role`: High-level operational role (e.g., `"Critic 多维结构化打分函数"`, `"五分钟敏捷早筛适应度打分函数"`).
- `explanation_priority`: `MUST_EXPLAIN | CONCISE_DEFINE | AUDIT_ONLY`.
- `symbol_definitions`: List of symbols with explicit meanings, dimensions, and domains.
- `input_output`: Explicit input and output specifications.
- `term_interpretations`: Term-by-term breakdown explaining intuitive mechanical effects of operators, signs, fractions, and exponents.
- `assumptions`: Explicit theoretical and experimental assumptions.
- `implementation_proxy`: Distinguishes practical engineering surrogates from theoretical ideals.
- `unspecified_details`: Highlights hyperparameters, thresholds, or code details omitted by the paper.

### 2.2 Pedagogical Presentation & Rendering
- **`scripts/render_paper_reader.py`**:
  - HTML rendering enriched with `.eq-role` badge, `.eq-terms` list, and `.eq-proxy` callout.
  - Markdown rendering enriched with `**角色定位**`、`**核心项解析与数学直觉**`、`**工程实现与代理说明**`.
  - Zero raw ASCII replacements and zero empty/silent equation cards.
- **`scripts/narrative_composer_agent.py`**:
  - Implemented `_compose_equation_pedagogy_narrative` to weave operational roles, term interpretations, and proxies into coherent Chinese scientific narrative.

### 2.3 Independent Pedagogical Audit Tool
Created `scripts/reader_math_explanation_audit.py`:
- Audits whether all `MUST_EXPLAIN` formulas are pedagogically taught.
- Employs sentence-level, negation-aware contradiction detection:
  - Rejects false claims that $1 - B_t$ rewards bottlenecks.
  - Rejects false claims that the system directly calculated full-parameter second-order Hessians.
- Enforces concise definitions for auxiliary/notation formulas.
- Integrated into `scripts/reader_acceptance.py` release gate.

---

## 3. Per-Formula Pedagogical Review

### 3.1 RingMoClaw (arXiv:2609.00814v2)

| Equation | Priority | Role & Mathematical Function | Pedagogical Breakdown & Key Insights |
| :--- | :---: | :--- | :--- |
| **Eq. (1)** | `MUST_EXPLAIN` | Critic 综合多维评价打分函数<br>$\text{Score}_t = w_1 C_t + w_2 (1 - B_t) + w_3 H_t$ | • **$1 - B_t$ 瓶颈反转**：$B_t \in [0, 1]$ 度量瓶颈严重度。取 $1 - B_t$ 将惩罚项反转为可用度：无瓶颈得满分，严重瓶颈得分骤降至 0，迫使系统优先解决瓶颈。<br>• **$w_1 C_t$**：正向牵引阶段目标完成度。<br>• **$w_3 H_t$**：全局经验先验正则化，避免盲目搜索。<br>• **静态权重**：方案 (0.3, 0.5, 0.2)，数据 (0.35, 0.4, 0.25)，结果 (0.5, 0.3, 0.2)。 |
| **Eq. (2)** | `MUST_EXPLAIN` | Main Agent 全局决策状态转移算子<br>$o_{\text{main}}^{t+1} = \Pi_{\text{update}}(s_t, \{c_t, \text{Score}_t\})$ | • **闭环决策转移**：依据量化评分 $\text{Score}_t$ 与细粒度诊断 $c_t$ 触发 Accept/Revise/Reject/Escalate 四级调度。<br>• **工程实现**：通过 LLM Prompt 编排与条件分支执行，非参数化强化学习网络。 |
| **Eq. (3)** | `CONCISE_DEFINE` | 遥感四维结构化搜索空间<br>$\mathcal{S} = \{\mathcal{S}_{\text{arch}}, \mathcal{S}_{\text{train}}, \mathcal{S}_{\text{data}}, \mathcal{S}_{\text{intg}}\}$ | 将端到端遥感算法设计解耦为架构、训练策略、数据工程与系统集成四维正交子空间，防止组合爆炸。 |
| **Eq. (4)** | `CONCISE_DEFINE` | 外部可复用算子元组<br>$\omega = \{I, O, F, P\}$ | 剥离外部代码仓库环境依赖，提炼输入张量签名 $I$、输出签名 $O$、前向逻辑 $F$ 与超参分布 $P$。 |
| **Eq. (5)** | `MUST_EXPLAIN` | 跨任务全局经验增量更新规则<br>$\mathcal{M}_{\text{gb}} \leftarrow \mathcal{M}_{\text{gb}} \cup \text{Filter}(\mathcal{M}_{\text{loc}}, \text{Score}_t)$ | • **质量门控**：$\text{Filter}$ 基于 $\text{Score}_t$ 准入门槛过滤局部试验噪声，仅沉淀高分创新与典型失败模式。<br>• **$\cup$ 累积**：跨任务增量沉淀形成演化经验总线。 |
| **Eq. (6)** | `MUST_EXPLAIN` | 五分钟敏捷早筛综合适应度评分<br>$f_{\text{score}}(m) = \alpha \left(\frac{\Delta \text{Acc}}{\Delta t}\right) + \beta \exp\left(-\sigma \|\nabla_\theta^2\|\right)$ | • **$\frac{\Delta \text{Acc}}{\Delta t}$**：单位时间精度收益率（初期收敛加速度）。<br>• **$\exp(-\sigma \|\nabla_\theta^2\|)$**：二阶曲率指数衰减惩罚，曲率平缓趋于 1，剧烈震荡迅速趋于 0。<br>• **【关键工程代理】**：直接计算全参数 Hessian 矩阵开销过大，工程实现以最后 50 步 loss 变异系数 $\text{CV}_{50}$ 作为平稳性轻量代理；综合评分 $>0.55$ 晋级全量资源；原文未公开 $\alpha, \beta, \sigma$ 确切数值。 |
| **Eq. (7)** | `CONCISE_DEFINE` | 早筛与全量排名的 Spearman 秩相关系数<br>$\rho = 1 - \frac{6 \sum d_i^2}{N(N^2 - 1)}$ | 评估五分钟早筛与全量最终排名的单调一致性，实测 $\rho = 0.64$ ($p=0.03$)。 |

### 3.2 Cross-Paper Generalization Benchmarks

| Benchmark Paper | Equation | Priority | Mathematical Teaching Breakdown |
| :--- | :--- | :---: | :--- |
| **Attention** (`bdfaa68d`) | Eq. (1) | `MUST_EXPLAIN` | **缩放点积注意力**：深入解析 $\frac{1}{\sqrt{d_k}}$ 尺度因子的作用：当键维度 $d_k$ 很大时，向量点积方差增大至 $d_k$，迫使 softmax 进入梯度极小的平坦饱和区域（梯度消失）。除以 $\sqrt{d_k}$ 将方差拉回 1，维持反向传播稳定流动。 |
| **LoRA** (`e9a0d312`) | Eq. (3) | `MUST_EXPLAIN` | **低秩权重更新分解**：深入解析 $\Delta W = BA$ 重参数化将高维稠密更新约束在内在低维流形上；解析 $\frac{\alpha}{r}$ 恒定缩放系数的作用在于固定 $\alpha$ 时调整秩 $r$ 无需重新调优学习率，保持优化稳定性。 |

---

## 4. Adversarial Counterexample & Rejection Tests

| Test Case | Scenario / Description | Expected Audit Behavior | Result |
| :--- | :--- | :--- | :--- |
| **Silent Formula** | Eq. (1) rendered with only a 4-character title `"打分公式"` | Audit rejects with `UNEXPLAINED_MATERIAL_EQUATION` | **PASSED** (Rejected) |
| **Inverted Sign** | Text asserts that higher bottleneck $B_t$ leads to higher score | Audit rejects with `MATHEMATICAL_CONTRADICTION` | **PASSED** (Rejected) |
| **False Hessian Claim** | Text asserts that system directly calculated exact second-order Hessian | Audit rejects with `MATHEMATICAL_CONTRADICTION` | **PASSED** (Rejected) |
| **Auxiliary Definition** | Eq. (3) search space tuple defined in 1 concise, meaningful sentence | Audit passes concise definition | **PASSED** (Accepted) |

---

## 5. Test Suite Verification Receipts

- **`tests/test_math_pedagogy.py`**:
  - `test_schema_validates_rich_pedagogy`: **PASSED**
  - `test_ringmoclaw_pedagogy_teaches_core_equations`: **PASSED**
  - `test_cross_paper_pedagogy_attention_and_lora`: **PASSED**
  - `test_adversarial_counterexamples_rejected_by_audit`: **PASSED**
  - `test_end_to_end_rendered_reader_contains_pedagogy`: **PASSED**
- **Combined Acceptance Gate**:
  - `pytest tests/test_equation_fidelity.py tests/test_math_pedagogy.py tests/test_reader_acceptance.py`: **24 passed, 0 failed** in 15.66s.
- **Full Repository Regression**:
  - `pytest`: **248 passed, 0 failed** in 109.92s.

---

## 6. Issue #40 Resolution & Conclusion

All acceptance criteria for GitHub Issue #40 are satisfied:
- Reader teaches core equations step-by-step with term breakdowns and intuitive rationales.
- Engineering proxies (such as $\text{CV}_{50}$ for Eq. 6) and unstated parameters are explicitly called out.
- Non-RingMo papers (Attention, LoRA) demonstrate generalizable, non-templated mathematical pedagogy.
- Adversarial counterexamples (silent equations, mathematical contradictions) are rejected.
- Rendered HTML and Markdown maintain presentation parity with clear visual hierarchy.

Ready to commit and close Issue #40. Proceeding strictly to Issue #41 (Source-Grounded Scientific Truth).
