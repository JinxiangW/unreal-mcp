# Legacy 层定位与退役清单

## 当前定位

`unreal_editor_mcp` 不再应被视为主要使用层。

现在它的定位是：

- internal
- fallback
- compatibility layer

也就是说：

- 对外主入口应逐步收口到 `unreal_orchestrator` 和各域高层命令
- `unreal_editor_mcp` 主要保留为底层执行基础设施和迁移过渡层

## 为什么现在还保留

### 1. 传输和连接基础设施仍在这里

- TCP 连接
- 通用 `send_command`
- 现有插件命令面

### 2. `run_python` 仍通过现有插件命令面进入 UE

### 3. 还有几个大域尚未迁移完成

- `material_graph`
- `niagara`
- `blueprint_info`
- `blueprint_graph`

## 哪些功能仍依赖 legacy 层

### 直接依赖

- `unreal_harness_runtime/python_exec.py`
- `unreal_editor_mcp.common.send_command`
- `unreal_editor_mcp.connection`

### 间接依赖

- `unreal_scene` 的 live editor python 执行
- `unreal_asset` 的 live editor create/update
- `unreal_material` 的 live editor 参数更新
- `unreal_diagnostics` 的 ready/health 探测

### 仍主要停留在 legacy 能力面

- `material_graph`
- `niagara`
- `blueprint_info`
- `blueprint_graph`

## 当前不应该怎么用

不建议把 `unreal_editor_mcp` 当成默认业务入口去直接猜 raw 字段和 raw 命令。

尤其不建议：

- 对灯光继续优先走裸 `set_actor_properties`
- 对复杂图编辑继续走扁平属性猜测
- 在多会话里直接拿大量 raw 工具并发轰同一个编辑器实例

## 当前推荐怎么用

- 场景相关：优先 `unreal_orchestrator` / `unreal_scene`
- 资产相关：优先 `unreal_orchestrator` / `unreal_asset`
- 材质资产/参数：优先 `unreal_orchestrator` / `unreal_material`
- 导入：优先 commandlet 路径

## 退役顺序

### Phase 1

- 停止把新业务能力直接加到 legacy raw 接口上
- 新功能优先进入新域 harness

### Phase 2

- 完成 `material_graph`
- 完成 `diagnostics`
- 补齐 orchestrator 的统一结果包装

### Phase 3

- 把 `niagara`
- `blueprint_info`
- `blueprint_graph`
逐步迁到新域边界下

### Phase 4

- 将 `unreal_editor_mcp` 明确降级为纯内部后端
- 对外文档不再把它列为默认入口

## 退役完成的判定标准

只有当下面条件大部分满足后，才适合进一步收缩 legacy 层：

- `scene` 不再依赖 raw 属性桥接作为主要路径
- `asset` 已完全走新链路
- `material asset/instance/parameter` 已完全走新链路
- `material_graph` 已建立独立能力面
- `diagnostics` 可稳定判断 ready / busy / commandlet 状态
- orchestrator 已成为高风险命令默认入口
