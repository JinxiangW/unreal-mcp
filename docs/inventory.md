# 功能清单总览

这份文档列出当前仓库里的功能全景，而不是只列高层命令或架构方向。

分为三类：

- 当前可用的 legacy/editor MCP 功能
- 新 harness 已迁移并可用的功能
- 已规划但尚未真正实现的功能

## 术语说明

### 真实环境回归

文档里之前写的“真实回归”，这里统一明确成“真实环境回归”。

含义：

- 不是只做语法检查
- 不是只做 mock
- 不是只看代码路径推断
- 而是在真实 UE 环境、真实项目、真实资产或真实关卡上下文里执行一次功能，再检查结果

这个说法来自常见工程术语：

- `regression test / 回归测试`

这里加上“真实环境”三个字，是为了和下面几类区分开：

- 语法检查
- 导入检查
- 单元级检查
- 纯静态代码检查

## 状态字段说明

- `状态`
  - `可用`: 当前可以直接使用
  - `部分可用`: 已有部分能力或依赖特定前提
  - `规划中`: 还未真正实现
- `执行后端`
  - `legacy tcp`
  - `live editor python`
  - `commandlet`
  - `mixed`
- `默认入口`
  - `orchestrator`
  - `domain harness`
  - `commandlet only`
  - `legacy fallback`
  - `internal/debug`
- `验证状态`
  - `已做真实环境回归`
  - `仅做基础验证`
  - `未验证`
- `结果校验状态`
  - `已接入`
  - `未接入`
  - `部分接入`
  - `目标要求`

## 1. Legacy / `unreal_editor_mcp` 当前可用功能

这些是当前底层仍然可直接调用的能力面。

但它的定位应理解为：

- internal
- fallback
- 迁移期兼容层

而不是后续默认推荐直接使用的主要业务入口。

### Asset

- `get_assets`
- `get_asset_properties`
- `create_asset`
- `set_asset_properties`
- `delete_asset`
- `batch_create_assets`
- `batch_set_assets_properties`
- `read_result_handle`
- `release_result_handle`

### Level / Viewport

- `get_current_level`
- `create_level`
- `load_level`
- `save_current_level`
- `get_viewport_camera`
- `set_viewport_camera`
- `get_viewport_screenshot`

### Actor / Scene

- `get_actors`
- `get_actor_properties`
- `spawn_actor`
- `set_actor_properties`
- `delete_actor`
- `batch_spawn_actors`
- `batch_delete_actors`
- `batch_set_actors_properties`

### Import

- `import_texture`
- `import_fbx`

### Material / Material Graph

- `build_material_graph`
- `get_material_graph`

### Niagara

- `get_niagara_graph`
- `update_niagara_graph`
- `get_niagara_emitter`
- `update_niagara_emitter`
- `get_niagara_compiled_code`
- `get_niagara_particle_attributes`

### Blueprint Info / Content

- `get_blueprint_info`
- `update_blueprint`
- `read_blueprint_content`
- `analyze_blueprint_graph`

说明：

- 当前 raw 工具已做 wrapper 层 token 优化
- 查询类默认支持 `summary_only / fields / limit`
- 图类和 Blueprint 内容默认摘要返回
- 大结果支持 `saved_to` 与 `result_handle`

### Blueprint Graph

- `blueprint_graph_command`

支持的图命令：

- `add_blueprint_node`
- `connect_nodes`
- `create_variable`
- `set_blueprint_variable_properties`
- `add_event_node`
- `delete_node`
- `set_node_property`
- `create_function`
- `add_function_input`
- `add_function_output`
- `delete_function`
- `rename_function`

## 2. 新 Harness 当前已实现功能

默认使用规则：

- 如果用户或会话没有特别指定入口，默认按照“默认入口”这一列来调用
- 目前大多数高风险功能都应优先走 `orchestrator`

### 状态矩阵

| 域 | 功能 | 状态 | 执行后端 | 默认入口 | 验证状态 | 结果校验状态 |
| --- | --- | --- | --- | --- | --- | --- |
| orchestrator | `get_harness_domains` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| orchestrator | `get_domain_design` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| orchestrator | `route_harness_task` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| scene | `get_scene_harness_info` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| scene | `get_scene_backend_status` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| scene | `query_scene_actors` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| scene | `query_scene_lights` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| scene | `set_scene_light_intensity` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| scene | `create_spot_light_ring` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| scene | `aim_actor_at` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| scene | `set_post_process_overrides` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| scene | `spawn_actor_with_defaults` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| scene | `inspect_scene_python_enums` | 可用 | live editor python | domain harness | 已做真实环境回归 | 已接入 |
| asset | `get_asset_harness_info` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| asset | `query_assets_summary` | 可用 | legacy tcp wrapper | orchestrator | 已做真实环境回归 | 已接入 |
| asset | `ensure_folder` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| asset | `create_asset_with_properties` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| asset | `ensure_asset_with_properties` | 可用 | mixed | orchestrator | 已做真实环境回归 | 已接入 |
| asset | `duplicate_asset_with_overrides` | 可用 | mixed | orchestrator | 已做真实环境回归 | 已接入 |
| asset | `move_asset_batch` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| asset | `update_asset_properties` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| asset | `import_texture_asset` | 可用 | commandlet | orchestrator | 已做真实环境回归 | 已接入 |
| asset | `import_fbx_asset` | 可用 | commandlet | orchestrator | 已做真实环境回归 | 已接入 |
| material | `get_material_harness_info` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| material | `create_material_asset` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| material | `create_material_instance_asset` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| material | `update_material_instance_properties` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| material | `update_material_instance_parameters_and_verify` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| material | `get_material_instance_parameter_names` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| material | `set_material_instance_scalar_parameter` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| material | `set_material_instance_vector_parameter` | 可用 | live editor python | orchestrator | 已做真实环境回归 | 已接入 |
| material | `set_material_instance_texture_parameter` | 可用 | live editor python | orchestrator | 仅做基础验证 | 已接入 |
| material_graph | `get_material_graph_harness_info` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| material_graph | `analyze_material_graph` | 可用 | legacy tcp wrapper | domain harness | 已做真实环境回归 | 已接入 |
| material_graph | `create_material_graph_recipe` | 可用 | legacy tcp wrapper | domain harness | 已做真实环境回归 | 已接入 |
| material_graph | `connect_material_nodes` | 可用 | legacy tcp wrapper | domain harness | 已做真实环境回归 | 已接入 |
| diagnostics | `get_harness_health` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| diagnostics | `get_runtime_policy` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| diagnostics | `get_transport_port_status` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| diagnostics | `get_unreal_python_status` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| diagnostics | `get_editor_process_status` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| diagnostics | `get_commandlet_runtime_status` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| diagnostics | `get_editor_ready_state` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| diagnostics | `wait_for_editor_ready` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| diagnostics | `get_token_usage_summary` | 可用 | python | orchestrator | 已做真实环境回归 | 已接入 |
| diagnostics | `dev_launch_editor_and_wait_ready` | 可用 | python | internal/debug | 已做真实环境回归 | 已接入 |

### Orchestrator

目录：`unreal_orchestrator/`

已实现：

- `get_harness_domains`
- `get_domain_design`
- `route_harness_task`

### Scene

目录：`unreal_scene/`

状态：已开始切到 UE Python

已实现：

- `get_scene_harness_info`
- `get_scene_backend_status`
- `query_scene_actors`
- `query_scene_lights`
- `set_scene_light_intensity`
- `create_spot_light_ring`
- `aim_actor_at`
- `set_post_process_overrides`
- `spawn_actor_with_defaults`
- `inspect_scene_python_enums`

备注：

- 走 `run_python` 到编辑器内 Python
- 已有真实环境回归

### Asset

目录：`unreal_asset/`

状态：已切到混合执行模型

已实现：

- `get_asset_harness_info`
- `query_assets_summary`
- `ensure_asset_with_properties`
- `create_asset_with_properties`
- `update_asset_properties`
- `import_texture_asset`
- `import_fbx_asset`

执行模型：

- `create/update` 走 live editor `run_python`
- `import` 走独立 commandlet

### Material

目录：`unreal_material/`

状态：资产/实例/参数层已接上新链路

已实现：

- `get_material_harness_info`
- `create_material_asset`
- `create_material_instance_asset`
- `update_material_instance_properties`
- `update_material_instance_parameters_and_verify`
- `get_material_instance_parameter_names`
- `set_material_instance_scalar_parameter`
- `set_material_instance_vector_parameter`
- `set_material_instance_texture_parameter`

### Material Graph

目录：`unreal_material_graph/`

状态：已进入最小可用阶段

当前已实现：

- `get_material_graph_harness_info`
- `analyze_material_graph`
- `create_material_graph_recipe`
- `connect_material_nodes`

### Diagnostics

目录：`unreal_diagnostics/`

当前已实现：

- `get_harness_health`
- `get_runtime_policy`
- `get_editor_ready_state`
- `wait_for_editor_ready`
- `get_token_usage_summary`
- `get_transport_port_status`
- `get_unreal_python_status`
- `get_editor_process_status`
- `get_commandlet_runtime_status`
- `dev_launch_editor_and_wait_ready`（internal/debug）

## 3. 已规划但尚未完整实现的功能

### Scene

- `create_three_point_lighting`

### Asset

- 更完整的材质实例参数层返回结构

### Material Graph

- 图重构

### Orchestrator

- 真正的域级调度
- 统一错误模型
- 统一结果包装

### Diagnostics

- 更细的错误分类与持久化诊断

## 4. 现阶段最重要的边界

### 已适合使用的新链路

- `scene` 的高层命令与 compact 查询
- `asset` 的 create/update/import
- `asset` 的 ensure/query 工作流
- `material` 的资产/实例/参数层

### 仍依赖旧能力面或尚未拆分完成

- `material graph`
- `niagara`
- `blueprint info`
- `blueprint graph`

## 5. 建议阅读顺序

如果只想看“现在到底能用什么”：

1. 先看本文件 `inventory.md`
2. 再看 `commands.md`
3. 再看 `categories.md`
