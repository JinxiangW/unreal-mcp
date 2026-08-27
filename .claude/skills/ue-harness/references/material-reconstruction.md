# 材质重建规划（Material Reconstruction Planning）

> **Language convention**: conceptual strategy, decision rules, and explanations are in Chinese. Operational workflows, checklists, and verification gates are in English to match MCP tool names and code identifiers.

## 用途

将导出的材质包（如 Unity `manifest.json` 加可选的 `shadergraph.json`）转换为 `material-reconstruction-plan/0.1` 重建方案。

本文件仅负责规划（planning only），不替代 Unreal 执行工具。开始执行时请同时阅读 `../SKILL.md`。

## 阅读顺序

1. `material-package.md` — 材质包格式
2. `material-reconstruction-plan.md` — 重建方案格式
3. 包中的 `manifest.json`（如果有）
4. 包中的 `shadergraph.json`（如果有）
5. `D:\ue-mcp\unreal-mcp\docs\examples\` 下的对应包示例（如果有）

## 工作流

核心纪律（Core discipline）：

- Do not skip stages
- Do not jump from package inspection straight to arbitrary UE graph edits
- Do not claim alignment from visual impression alone
- Do not treat `success: true` from one MCP call as proof of correctness

### 1. 检查包（Inspect the Package）

提取以下信息（中文标注类别，英文匹配字段名）：

**基础信息：**
- source engine and shader family
- surface settings: blend, alpha clip, two-sided, domain
- transferable semantics: baseColor, normal, metallic, roughness, emission, opacity, occlusion
- texture resources and import hints
- graph evidence availability
- warnings, missing subgraphs, and confidence notes

**对于 Unity Shader Graph 包，还需检查：**

- whether `shadergraph.json` exists
- whether subgraph exports exist
- whether any `CustomFunctionNode` exists
- whether copied shader sources exist under `shader_sources/`
- whether runtime-only graph inputs exist and whether matching runtime state was exported

约束（中文）：

- 如果存在自定义函数但缺少其源码证据，先停下来修复导出（fix export first）
- 如果某分支依赖运行时状态（世界空间数组、场景驱动遮罩或全局 shader 值），先导出该运行时状态再将此分支标记为可重建

### 2. 选择重建模式（Choose a Reconstruction Mode）

优先选择以下模式之一：

- `semantic_surface`
- `graph_guided_semantic_surface`
- `manual_custom_graph`
- `partial_reconstruction`

决策规则（Decision rule）：

- if semantics are sufficient and runtime-only graph logic is missing, stay in `semantic_surface`
- if graph evidence is useful but only part of it is safely reconstructable, use `graph_guided_semantic_surface`
- if a branch depends on missing runtime evidence, mark that branch unresolved instead of guessing
- Do not default to exact graph replay when the source exposes opaque slot ids, missing subgraph bodies, or source-specific node types

### 3. 构建方案（Build the Plan）

Always emit these sections:

- `strategy`
- `resourceBindings`
- `execution`
- `approximations`
- `unresolved`
- `verificationGoals`

When execution is expected in the same task, also emit:

- `executionOrder`
- `stopConditions`
- `validationGate`
- `verificationArtifacts`

保持边界清晰：

- `strategy`, `approximations`, and `unresolved` explain planning decisions
- `resourceBindings`, `execution`, and `verificationGoals` are execution-facing

#### 3.1 函数策略（Function Strategy）

当源图已有有意义的子图边界时，在方案中保留这些边界。

Planning rules:

- plan by source subgraph or semantic branch, not by tiny arithmetic steps
- record whether each planned function is expected to be:
  - a project-local reusable function
  - an engine-function reuse
  - a native-node rebuild
  - a small custom fragment
- if the source subgraph is a custom function, preserve that dependency explicitly in the plan unless a clearly better native equivalent is already known
- if the source subgraph depends on external source files or runtime arrays, record those dependencies as required evidence before the branch can be claimed complete
- do not silently replace a source custom subgraph with a guessed scalar or constant

Detailed execution rules for function reuse, custom-node constraints, and stop conditions live in `../SKILL.md`.

### 4. 应用布局规则（Apply Layout Rules）

When generating `execution.graph.recipe.nodes`, choose readable coordinates.

Default layout:

- left-to-right flow
- shared inputs on the far left
- one semantic lane per output group
- utility nodes in the middle
- material outputs on the right

Recommended lanes:

- `BaseColor`
- `Opacity` or `OpacityMask`
- `Normal`
- `Metallic`
- `Roughness`
- `AmbientOcclusion`
- `Emissive`
- custom branches below the core PBR lanes

Recommended placement rules:

- place texture coordinates near the top-left
- place texture and parameter nodes in the first working column
- place combine or transform nodes in the second column
- place the final node of each lane close to the material output
- avoid crossings when a simple lane layout can remove them
- add reroute nodes in the plan when a branch requires a long shared route

### 5. 交付给 UE 执行（Hand Off to UE Execution）

When execution begins, follow the material execution order, stop conditions, and validation rules in `../SKILL.md`. This planner should not duplicate those execution instructions.

### 6. 记录近似替换和未解决项（Record Approximations and Unresolved Logic）

概念说明（中文）：简化源码行为时要明确说明。

Common approximations:

- roughness derived from smoothness
- alpha inferred from base texture alpha
- default lit used instead of source custom lighting
- guide texture imported but left unconnected
- AO left unconnected when only an occlusion-strength control exists without an occlusion texture

Common unresolved items:

- missing subgraph bodies
- source-specific dissolve logic
- vertex displacement or wind branches
- insufficient port semantics for exact replay
- runtime global arrays not yet exported
- scene-driven mask transforms not yet exported
- source-side object references not stored in the material asset itself
- keyword-controlled branch families without active runtime state

## 输出标准（Output Standard）

Output one converged `material-reconstruction-plan/0.1` JSON object.

Prefer:

- stable field names
- short machine-usable strings in `execution`
- long-form reasoning only in `strategy.reason`
- specific `verificationGoals` for properties, output connections, and resource bindings

Recommended `verificationArtifacts`: exported package path, UE material path, UE function paths, verification script path, verification report path.

## 验证门槛（Validation Gate）

Do not claim reconstruction alignment until all of the following are true:

- the source package contains the graph evidence required by the chosen plan
- runtime evidence exists for every runtime-dependent branch that is claimed reconstructed
- UE material compilation and readback validation pass according to `../SKILL.md`
- parameter grouping is readable and aligned
- a machine-readable verification report exists and passes
