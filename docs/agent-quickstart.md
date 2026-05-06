# Agent Quickstart

默认优先连接 `python -m unreal_mcp.slim_server`。它只暴露发现、路由、ready 和 token 诊断工具，避免 agent 冷启动加载全量工具 schema。

## 使用顺序

1. 用 `route_harness_task` 或 `get_harness_domains` 判断任务 domain。
2. 用 `get_domain_design` 查看对应 `server_module` 和推荐启动参数。
3. 只启用当前任务需要的 domain server，例如 `python -m unreal_scene.server`。
4. 高风险 live-editor 操作前用 `get_editor_ready_state` 或 `wait_for_editor_ready`。
5. 需要跨域或兼容旧流程时，才使用 `python -m unreal_mcp.server` 全量入口。

## Domain 选择

- `scene`：Actor、灯光、关卡、viewport、后处理。
- `asset`：资产查询、CRUD、导入、贴图属性、批处理。
- `material`：材质资产、材质函数资产、材质实例和参数。
- `material_graph`：材质图节点、连线、属性连接、patch、readback。
- `blueprint_info` / `blueprint_graph`：蓝图读取、节点查找、图编辑。
- `diagnostics`：ready、transport、commandlet、token 诊断。

## Token 禁忌

- 不要默认打开 full server 暴露 78 个工具。
- 不要用 raw `get_actors` / `get_assets` 做大范围浏览，优先用 domain 查询工具。
- 图查询默认用摘要；需要完整图时用 result handle，并通过 `path + offset + limit + fields` 分页读取。
- 只在确实需要时传 `include_full_graph=True`。
