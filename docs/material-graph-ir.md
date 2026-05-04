# 材质图 IR 方案

本文档描述内部翻译层。

不是面向用户的包契约，也不是面向 agent 的规划契约。

推荐的顶层工作流：

1. 源工具导出 agent 可读的 `material package`
2. Agent 读取包并生成 UE `reconstruction plan`
3. 内部翻译辅助工具可将部分数据规范化为更小的标准 IR 后再构建 UE recipe
4. Unreal MCP 执行 UE recipe 并验证结果

## 目标

提供稳定的中间表示，使 agent 能从外部 JSON 源重建 Unreal 材质图，而不将 Unreal 构建器耦合到 Unity 特定负载。

预期流水线：

1. 外部源导出 JSON
2. 源特定翻译器将其规范化为标准 IR
3. UE 侧翻译器将标准 IR 转换为 UE 材质 recipe
4. `material_graph` 构建器创建节点、连接边、应用材质属性并验证结果

## 已观测的源格式

### Unity 材质导出包

观测于 `D:\unity-mcp\exports\Wing_L\manifest.json`。

特征：

- 具备良好的 PBR 风格重建迁移语义
- 包含材质元数据、表面设置、贴图、贴图用法和规范化语义
- 不包含显式的引擎无关图
- 最适合 `semantic_surface` IR，而非直接图回放

### Unity ShaderGraph 导出

观测于 `D:\unity-mcp\exports\Wing_L\shadergraph.json`。

特征：

- 包含结构图信息：节点、边、属性、关键字、输出块
- 节点 `type` 值仍为 Unity 特定
- 边连接使用 Unity slot id，而非稳定的跨引擎引脚名
- 未暴露足够的跨引擎语义以直接作为 UE 构建器输入
- 最适合 `explicit_graph_snapshot` IR，仍需要源特定翻译

## 标准 IR

标准 IR 应支持两种图类型：

### 1. `semantic_surface`

当源可以描述材质意图但无法描述可复用的跨引擎节点图时使用。

推荐结构：

```json
{
  "schema_version": "material-graph-ir/0.1",
  "source": {
    "format": "unity-material-export-spec/1.0"
  },
  "graph": {
    "kind": "semantic_surface",
    "asset": {
      "name": "Wing_L",
      "path": "Assets/Art/Wings/Wing_L.mat"
    },
    "material": {
      "blend_mode": "Masked",
      "shading_model": "DefaultLit",
      "two_sided": true
    },
    "resources": [
      {
        "id": "baseColor",
        "kind": "texture2d",
        "semantic": "baseColor"
      }
    ],
    "semantics": {
      "baseColor": {},
      "normal": {},
      "metallic": {},
      "roughness": {},
      "emission": {},
      "opacity": {},
      "occlusion": {}
    },
    "metadata": {}
  }
}
```

这是当前 Unity 材质包导出的正确目标格式。

### 2. `explicit_graph`

当源已描述图节点和边时使用。

推荐结构：

```json
{
  "schema_version": "material-graph-ir/0.1",
  "source": {
    "format": "unity-shadergraph-export/1.0"
  },
  "graph": {
    "kind": "explicit_graph",
    "asset": {},
    "nodes": [],
    "edges": [],
    "outputs": [],
    "resources": [],
    "metadata": {}
  }
}
```

重要规则：

- `explicit_graph` 必须尽可能使用稳定的节点 id 和命名的输入/输出
- 不透明的源 slot id 可保留在 `metadata` 中，但不应成为 UE 构建器的长期执行契约

## UE Recipe 边界

当前 UE 构建器仍消费 UE 特定的 recipe：

- `nodes`
- `connections`
- `properties`

该 recipe 应保持 UE 特定。标准 IR 应翻译为它，而非直接替代它。

直接含义：

- 不要将 `get_material_graph` 导出格式作为标准 IR
- 不要将 Unity 导出 JSON 直接喂给 `build_material_graph`

## 翻译器边界

推荐拆分：

- `unity material export spec -> 标准 semantic_surface IR`
- `unity shadergraph export -> 标准 explicit_graph 快照`
- `标准 semantic_surface IR -> UE 材质 recipe`
- `标准 explicit_graph IR -> UE 材质 recipe`

只有最后一步应依赖 Unreal 节点名和构建器负载细节。

## 首个里程碑

1. 在 `unreal_material_graph/ir.py` 中添加标准 IR 辅助工具
2. 支持 `unity-material-export-spec/1.0 -> semantic_surface IR`
3. 支持 `semantic_surface IR -> UE recipe`，覆盖核心 PBR 子集：
   `baseColor`、`normal`、`metallic`、`roughness`、`emission`、`opacity`、`occlusion`
4. 显式保留未解决的资源绑定，而非静默丢弃贴图
5. 添加黄金测试数据：
   `unity manifest`、`unity shadergraph 快照`、`标准 IR`、`生成的 UE recipe`

## 已知待修复缺口

- UE 侧构建器和导出器在贴图/资源字段上仍有协议漂移风险
- Unity ShaderGraph 边当前暴露 slot id，而非稳定引脚名
- Alpha cutoff 及部分高级表面设置需要显式的 UE 侧处理
- 自定义 ShaderGraph 逻辑和子图需要源特定翻译器，而非通用构建器分支
