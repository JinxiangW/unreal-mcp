# 材质包

## 用途

`material package` 是给 agent 阅读的源侧交付格式。

不要求是严格的跨引擎 IR。优化目标为：

- LLM agent 可读性
- 保留源证据
- 提供足够的语义信息来规划 UE 重建
- 提供足够的原始结构来诊断复杂自定义图

包应保留源真相，不应过早强制套用僵硬的跨引擎图模型。

## 工作流角色

预期流水线：

1. Unity 或其他源导出工具输出 `material package`
2. Agent 读取包并推断 UE 重建策略
3. Agent 输出 `reconstruction plan`
4. Unreal MCP 执行方案

## 包目录

推荐目录布局：

```text
<MaterialName>/
  manifest.json
  shadergraph.json                # 可选
  subgraphs/
    index.json                    # 可选
    *.json                        # 可选
  textures/
    <exported texture files>      # 可选但推荐
```

注意：

- `manifest.json` 必需
- `shadergraph.json` 可选，但当源材质由图驱动且导出器可检查时应该存在
- `subgraphs/` 可选
- 贴图二进制文件可放在包根目录以保持向后兼容，但 `textures/` 是新导出的首选目标

## Manifest 目标

`manifest.json` 应直接回答以下问题：

- 导出了什么材质
- 来自哪个 shader/管线
- 材质适合语义重建、图感知重建还是仅部分迁移
- 存在哪些贴图和非贴图参数
- 哪些表面设置在 UE 中重要
- agent 必须考虑的警告或模糊点
- 可选的图证据文件在哪里

## 推荐 Manifest 结构

```json
{
  "schemaVersion": "material-package/0.1",
  "source": {
    "engine": "Unity",
    "tool": "unity-mcp",
    "toolSchema": "unity-material-export-spec/1.0",
    "exportedAtUtc": "2026-04-05T12:00:00Z"
  },
  "material": {
    "name": "Wing_L",
    "path": "Assets/Art/Wings/Wing_L.mat",
    "guid": "..."
  },
  "shader": {
    "name": "Shader Graphs/World Dissolve Smooth",
    "path": "Assets/Shaders/World Dissolve Smooth.shadergraph",
    "guid": "...",
    "pipeline": "HDRP",
    "isGraphDriven": true
  },
  "classification": {
    "reconstructionMode": "semantic_surface_with_graph_evidence",
    "confidence": 0.45,
    "notes": []
  },
  "surface": {
    "surfaceType": "Opaque",
    "blendMode": "Masked",
    "alphaClip": true,
    "alphaCutoff": 0.309,
    "twoSided": true
  },
  "semantics": {
    "baseColor": {},
    "normal": {},
    "metallic": {},
    "roughness": {},
    "emission": {},
    "opacity": {},
    "occlusion": {},
    "custom": []
  },
  "textures": [],
  "parameters": {
    "rawProperties": [],
    "keywords": {}
  },
  "graphEvidence": {
    "mainGraphFile": "shadergraph.json",
    "subgraphIndexFile": "subgraphs/index.json",
    "available": true
  },
  "warnings": []
}
```

## 必需顶层字段

- `schemaVersion`
- `source`
- `material`
- `shader`
- `classification`
- `surface`
- `semantics`
- `textures`
- `warnings`

## `classification.reconstructionMode`

推荐值：

- `semantic_surface`
  当导出器能提供可靠的表面语义且图细节缺失或无用。

- `semantic_surface_with_graph_evidence`
  当表面语义是主重建路径，但图文件可作为支持证据。

- `graph_snapshot`
  当导出器只能提供图结构且迁移语义非常有限。

- `partial_transfer_only`
  仅部分贴图/参数可靠，完整图重建不现实。

## `semantics`

此部分应尽量 agent 友好且与源无关。

推荐标准键：

- `baseColor`
- `normal`
- `metallic`
- `roughness`
- `emission`
- `opacity`
- `occlusion`
- `uvTransform`
- `custom`

每个语义条目可携带：

- `value`
- `textureId`
- `channel`
- `uv`
- `rawPropertyNames`
- `conversion`
- `enabled`
- 需要时的源特定额外字段

## `textures`

每个贴图条目应为可复用的证据记录，而不只是文件名。

推荐字段：

```json
{
  "id": "baseColor",
  "semantic": "baseColor",
  "asset": {
    "name": "T_Valkyrie_Wings",
    "path": "Assets/Art/Wings/T_Valkyrie_Wings.psd",
    "guid": "...",
    "type": "UnityEngine.Texture2D"
  },
  "packageFile": {
    "relativePath": "textures/Wing_L__BaseColor.psd",
    "exists": true
  },
  "sourceFile": {
    "absolutePath": "C:/Project/.../T_Valkyrie_Wings.psd",
    "exists": true
  },
  "usage": {
    "colorSpace": "sRGB",
    "isNormalMap": false,
    "uvSet": 0,
    "channelPacking": {}
  },
  "importHints": {}
}
```

## `graphEvidence`

此部分指向可选的图文件并总结其可信度。

推荐字段：

- `available`
- `mainGraphFile`
- `subgraphIndexFile`
- `schema`
- `nodeCount`
- `edgeCount`
- `limitations`

## 证据保留规则

包应保留源证据，即使 Unreal 尚未能完全使用。

示例：

- 保留 Unity keywords
- 保留原始属性名
- 保留图节点类型和 slot id
- 保留警告和置信度说明

Agent 在规划时可忽略部分数据，但不应在导出时丢失。

## 首个导出器目标

对于当前 Unity 导出器，近期目标应为：

- 保留当前 `manifest.json` 的优势
- 重命名或包装为 `material package`
- 显式标明图证据引用
- 将复制的贴图移到 `textures/` 下
- 将 Unity 特定数据保存在明确命名的源字段下，而非假装已是规范格式
