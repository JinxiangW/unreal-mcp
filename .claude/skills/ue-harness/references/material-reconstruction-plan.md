# 材质重建方案

## 用途

`reconstruction plan` 是 agent 为 Unreal MCP 编写的执行契约。

应描述：

- agent 决定在 UE 中构建什么
- 哪些源证据支持该决策
- 哪些部分是精确的、哪些是近似的
- 必须执行哪些 Unreal 操作
- 执行后必须验证什么

这是 agent 推理输出的正确位置。

## 工作流角色

预期流水线：

1. 源导出工具输出 `material package`
2. Agent 读取包并决定重建策略
3. Agent 输出 `reconstruction plan`
4. Unreal MCP 执行方案
5. Unreal MCP 验证结果并返回机器可读的证据

## 设计原则

- agent 和确定性工具均可读
- 近似替换要明确标注
- 未解决项要明确标注
- 资源绑定要明确
- 验证期望要明确

## 推荐顶层结构

```json
{
  "schemaVersion": "material-reconstruction-plan/0.1",
  "planId": "material-plan:Wing_L:2026-04-05T12:00:00Z",
  "sourcePackage": {
    "root": "D:/exports/Wing_L",
    "manifest": "D:/exports/Wing_L/manifest.json"
  },
  "target": {
    "projectPath": "/Game/Materials/Wings",
    "materialName": "M_Wing_L",
    "materialInstanceName": null
  },
  "strategy": {
    "mode": "semantic_surface",
    "reason": "Unity export provides reliable PBR semantics but graph snapshot lacks stable pin names and node parameters.",
    "confidence": 0.74
  },
  "resourceBindings": [],
  "execution": {},
  "approximations": [],
  "unresolved": [],
  "verificationGoals": []
}
```

## 必需顶层字段

- `schemaVersion`
- `planId`
- `sourcePackage`
- `target`
- `strategy`
- `resourceBindings`
- `execution`
- `approximations`
- `unresolved`
- `verificationGoals`

## 收敛规则

为使方案可跨 agent 和执行流程复用，应在概念上分为两层：

- **决策层**：包含 `strategy`、`approximations` 和 `unresolved`。agent 在此解释意图、置信度、权衡和缺口。
- **执行层**：包含 `resourceBindings`、`execution` 和 `verificationGoals`。尽可能确定性，避免长篇推理。

实际规则：

- `strategy.reason` 可以较长；`execution` 内的字段不应长篇
- `execution` 应优先使用面向 MCP 的结构，而非叙述性文本
- `resourceBindings` 应足够明确，使另一个 agent 无需重读源包即可导入或复用资源
- `verificationGoals` 应最小化、稳定且机器可检查
- 尚不能执行的源证据应归入 `unresolved`，而非放入 `execution` 的临时字段

## 示例

收敛示例见：

- `D:\ue-mcp\unreal-mcp\docs\examples\material-reconstruction-plan-wing_l.json`
- `D:\ue-mcp\unreal-mcp\docs\examples\material-reconstruction-plan-wing_l-layout-v2.json` — 此变体保持相同的首轮语义策略，但使用更清晰的分通道节点布局

## `strategy.mode`

推荐值：

- `semantic_surface`：从语义通道和已知材质约定重建 UE 图
- `graph_guided_semantic_surface`：主要从语义重建，但尽可能利用图证据来消除歧义或延续自定义逻辑
- `manual_custom_graph`：当 agent 有足够信心指定精确节点和连接时构建自定义图
- `material_instance_only`：复用已知 UE 父材质，仅设置参数/贴图
- `partial_reconstruction`：仅重建可靠子集，其余记录为未解决

## `resourceBindings`

此部分将包资源桥接到 UE 资产。

推荐条目结构：

```json
{
  "resourceId": "baseColor",
  "packageFile": "textures/Wing_L__BaseColor.psd",
  "ueAssetPath": "/Game/Imported/Wings/T_Wing_L_BaseColor",
  "status": "needs_import",
  "usageHints": {
    "samplerType": "Color",
    "compression": "Default",
    "srgb": true
  }
}
```

推荐 `status` 值：

- `existing`
- `needs_import`
- `missing`
- `rejected`

## `execution`

此部分是面向 MCP 的执行方案。

推荐结构：

```json
{
  "material": {
    "create": true,
    "path": "/Game/Materials/Wings",
    "name": "M_Wing_L",
    "properties": {
      "shading_model": "DefaultLit",
      "blend_mode": "Masked",
      "two_sided": true
    }
  },
  "graph": {
    "recipe": {
      "nodes": [],
      "connections": [],
      "properties": {}
    }
  },
  "instance": null
}
```

### `execution.graph.recipe`

应匹配或直接翻译为当前 UE 材质图构建器的负载：

- `nodes`
- `connections`
- `properties`

关键点：

- 包面向 agent
- recipe 面向 Unreal 执行

## `approximations`

此部分记录有意偏离源行为的地方。

推荐条目结构：

```json
{
  "kind": "semantic_conversion",
  "source": "roughness",
  "decision": "Derived roughness from Unity smoothness using OneMinus.",
  "impact": "May differ from source shader if the graph modifies smoothness downstream."
}
```

推荐近似类型：

- `semantic_conversion`
- `graph_simplification`
- `resource_substitution`
- `output_mapping_guess`
- `uv_mapping_assumption`

## `unresolved`

此部分记录 agent 无法安全转换为 UE 操作的源证据。

推荐条目结构：

```json
{
  "kind": "custom_graph_logic",
  "source": "custom.guideTexture",
  "reason": "No stable UE-side equivalent has been defined yet.",
  "evidence": {
    "rawPropertyNames": ["_GuideTexture", "_GuideTiling", "_GuideStrength"]
  },
  "severity": "warning"
}
```

推荐未解决类型：

- `missing_texture_binding`
- `custom_graph_logic`
- `subgraph_translation_missing`
- `unknown_node_type`
- `insufficient_port_semantics`

## `verificationGoals`

此部分定义 MCP 层执行后必须验证的内容。

推荐条目结构：

```json
[
  {
    "kind": "material_property",
    "field": "blend_mode",
    "expected": "Masked"
  },
  {
    "kind": "graph_output_connected",
    "output": "BaseColor"
  },
  {
    "kind": "graph_output_connected",
    "output": "Normal"
  },
  {
    "kind": "resource_bound",
    "resourceId": "baseColor",
    "expectedAssetPath": "/Game/Imported/Wings/T_Wing_L_BaseColor"
  }
]
```

## 最小可行方案

对于当前 Unity 工作流，最小可行方案应支持：

- 创建材质
- 导入或绑定贴图
- 构建核心 PBR 图
- 记录近似替换
- 记录未解决的自定义逻辑
- 请求图验证

这足以使 agent 在解决任意 Shader Graph 翻译之前就具备实用价值。

## 推荐的近期执行模式

### 模式 A：语义重建

使用：

- `manifest.json`
- 语义通道
- 贴图绑定
- 表面设置

忽略：

- 大部分图内部结构，仅作证据参考

### 模式 B：图引导重建

使用：

- 语义通道作为主路径
- 图证据检测特殊输出、自定义分支或子图使用

不要求：

- 精确的 Unity 逐节点回放

### 模式 C：精确自定义 recipe

仅当 agent 有足够证据指定精确 UE recipe 时使用。

应为 opt-in 且需满足置信度门槛，不应作为默认选项。
