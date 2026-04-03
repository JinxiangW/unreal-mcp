# 新 Harness 架构方案 v0.1

## 目标

这版方案服务三个目标：

1. 稳定优先
2. 可维护性优先
3. 保持一个全局可控入口，但内部按问题域拆分

## 核心结论

不建议继续维护一个“大而全”的单体 C++ 属性路由型 harness。

也不建议继续把 `unreal_editor_mcp` 作为默认对外业务入口。

它应逐步降级为：

- internal backend
- compatibility layer
- fallback path

建议改为：

- 对外：一个总控入口 `unreal-orchestrator`
- 对内：多个按问题域拆分的子 harness
- 执行层：`Scene / Asset / Material Asset` 优先切到 UE Python
- 保留层：Blueprint Graph、部分 Niagara、传输与桥接保留在 C++ 插件

## 推荐结构

### 对外入口

- `unreal-orchestrator`

职责：

- 识别任务类型
- 路由到子 harness
- 做 preflight
- 统一错误模型
- 汇总验证结果

### 子 harness 列表

- `unreal-scene`
- `unreal-asset`
- `unreal-material`
- `unreal-material-graph`
- `unreal-niagara`
- `unreal-blueprint-info`
- `unreal-blueprint-graph`
- `unreal-diagnostics`

## 每个子 harness 的职责边界

### 1. unreal-scene

后端：UE Python

覆盖：

- 场景灯光
- 后处理
- Actor 创建 / 删除 / 批量摆放
- transform
- 关卡操作
- 视口截图与相机

建议提供高层命令，而不是裸属性写入：

- `create_spot_light_ring`
- `aim_actor_at`
- `set_light_intensity`
- `set_post_process_overrides`
- `spawn_actor_with_defaults`

### 2. unreal-asset

后端：UE Python

覆盖：

- 通用资产 CRUD
- 路径查询
- 资产属性修改
- 批量操作
- 导入

### 3. unreal-material

后端：UE Python

覆盖：

- 材质创建
- 材质实例创建
- 参数设置
- 材质基础属性

### 4. unreal-material-graph

后端：C++ 主，必要时由 Python 做高层编排

覆盖：

- 材质节点创建
- 连线
- 材质图构建
- 材质图读取与分析
- 复杂图重构

原因：

- 长期看会走复杂材质图编辑
- 不建议一开始把复杂 graph editing 完全押在 UE Python 上

### 5. unreal-niagara

后端：混合

覆盖：

- emitter / graph 读取
- 常见图编辑
- 复杂能力先保留 C++

### 6. unreal-blueprint-info

后端：UE Python

覆盖：

- 蓝图结构读取
- 内容快照
- 分析与汇总

### 7. unreal-blueprint-graph

后端：C++ 插件主导

覆盖：

- 节点增删
- 连线
- 变量
- 函数
- 事件图修改

原因：

- 这是高复杂度图编辑域
- 不建议第一阶段转到 Python

### 8. unreal-diagnostics

后端：混合

覆盖：

- 能力探测
- UE 日志检查
- 命令注册一致性检查
- 回归验证

## 为什么 Scene / Asset / Material Asset 先转 UE Python

### Scene

当前问题暴露出：

- Actor / Component / Struct 模型不适合长期靠通用属性反射硬写
- 场景灯光和后处理天然是编辑器语义问题，不是简单 JSON 写属性问题

### Asset

- 资产工作流和 EditorAssetLibrary / AssetTools 贴得更近
- Python 侧维护成本更低

### Material

- 材质资产和材质实例管理适合 UE Python
- 但复杂材质图编辑应拆到 `unreal-material-graph`
- 不再把“材质资产管理”和“复杂材质图编辑”混成一个域

## C++ 插件应保留什么

- TCP 服务
- 命令注册和 capability registry
- Blueprint Graph 编辑
- Python 不足的底层能力
- 一致的响应格式和错误码

## 建议清理的旧实现

### 优先清理

- 场景编辑相关的高层属性路由
- 通用 `set_actor_properties` 中承担业务语义的部分
- 多处手工同步的命令表

### 暂时保留

- 传输层
- bridge
- Blueprint Graph
- Niagara 现有核心实现
- `unreal_editor_mcp` 作为 internal/fallback 层

## 错误模型建议

统一分为：

- `transport_error`
- `protocol_error`
- `capability_error`
- `validation_error`
- `runtime_error`
- `partial_apply`

这样后续 AI 不会把所有失败都误判为“连接断开”。

## 第一阶段落地顺序

### Phase 1

- 建立 `unreal-orchestrator`
- 建立新的能力分类和路由表
- 保留旧实现作为 fallback

### Phase 2

- 重写 `unreal-scene`
- 重写 `unreal-asset`
- 重写 `unreal-material`
- 设计 `unreal-material-graph` 的独立能力面

### Phase 3

- 逐步收缩旧 C++ 高层属性写入逻辑
- 让 scene / asset / material asset 默认只走 UE Python
- 保留 material graph 的 C++ 主实现

### Phase 4

- 梳理 Niagara 边界
- 整理 Blueprint Graph 单独能力面
- 统一回归测试和 diagnostics

## 目录建议

建议未来演化到类似结构：

```text
unreal-mcp/
  unreal_orchestrator/
  unreal_scene/
  unreal_asset/
  unreal_material/
  unreal_material_graph/
  unreal_niagara/
  unreal_blueprint_info/
  unreal_blueprint_graph/
  unreal_diagnostics/
  RenderingMCP/Plugins/UnrealMCP/
  docs/
```

## 当前建议

下一步最值得做的是：

1. 先定义 orchestrator 的输入/输出协议
2. 立刻抽出 `scene` 子 harness 的 UE Python 版本
3. 再把 `asset` 和 `material` 跟上
4. 单独定义 `material-graph`，不要混入普通材质资产流

这样最短路径就能把最容易出问题的一批编辑工作流从旧 C++ 属性路由中拿出来。
