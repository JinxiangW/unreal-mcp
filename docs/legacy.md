# Legacy 退役说明

`unreal_editor_mcp` 已从当前代码结构中移除。

## 已完成内容

- TCP transport 已迁入 `unreal_backend_tcp`
- raw wrapper 已迁入 `unreal_backend_tcp`
- `scene / asset / material_graph / diagnostics / runtime` 已改为依赖新 backend
- `unreal_editor_mcp` 包和 raw/internal server 入口已删除

## 当前结构

现在仓库里的分层是：

- `unreal_orchestrator`
  - 默认对外入口
- `unreal_scene / unreal_asset / unreal_material / unreal_material_graph / unreal_diagnostics`
  - 按域组织的 harness
- `unreal_backend_tcp`
  - 纯内部 TCP backend
  - 负责连接 Unreal 插件并封装剩余底层 raw 能力

## 仍然保留的底层能力

下面这些能力仍然存在，但不再通过 legacy 包名暴露：

- `get_current_level`
- `get_assets`
- `get_material_graph`
- `build_material_graph`
- Niagara 读写接口
- Blueprint info / content / graph 接口
- `read_result_handle / release_result_handle`

## 迁移后的使用规则

- 对外默认入口：`unreal_orchestrator`
- 对内底层 backend：`unreal_backend_tcp`
- 不再保留 `unreal_editor_mcp.server` 或 `unreal_editor_mcp.server_internal`

## 说明

这份文档保留的目的是记录：

- legacy 已经移除
- 哪些能力被平移到了新的内部 backend
- 后续不应再引入新的 legacy 包名依赖
