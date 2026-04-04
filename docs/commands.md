# 第一批高层命令清单

这份文档定义当前值得沉淀成高层命令的第一批工作流。

原则：

- 先覆盖高频、容易犯错、需要领域语义的任务
- 不把所有底层能力都包装成高层命令
- 高层命令随真实使用逐步增长

## Scene

### 已实现

- `set_scene_light_intensity`
  - 输入：actor、intensity、unit、mobility
  - 价值：避免只写 `Intensity` 忘记单位

- `create_spot_light_ring`
  - 输入：center、radius、z、count、target、intensity、unit、mobility
  - 价值：把批量摆灯、朝向、单位、可移动性收成一个配方
  - 返回：已补齐 `operation_id / post_state / verification / summary / items`

- `apply_scene_actor_batch`
  - 输入：`actor_specs`
  - 价值：把批量 spawn、朝向、灯光强度、后处理覆盖收成一个可复用的场景配方
  - 适合：批量布灯、批量场景搭建、批量 actor 初始化

- `delete_scene_actors_batch`
  - 输入：`delete_specs`
  - 价值：按类、名字、筛选条件批量删除 actor，并支持 `exclude_names / keep_count`
  - 适合：清灯、清批量测试 actor、保留一个主 PPV 并清理多余副本

- `query_scene_actors`
  - 输入：`actor_class`、`name_filter`、`limit`
  - 价值：把常见场景查询收成 compact 命令，减少 raw `get_actors`
  - 返回：统一包含 `summary / filters / items`

- `query_scene_lights`
  - 输入：`limit`
  - 价值：直接返回灯光摘要，避免先全量 actor 再筛灯光
  - 返回：统一包含 `summary / filters / items`

- `aim_actor_at`
  - 输入：`actor_name`、`target`、`preserve_roll`、`roll`
  - 价值：把朝向计算和回读验证收成一次调用

- `set_post_process_overrides`
  - 输入：`actor_name`、`overrides`
  - 价值：覆盖 flag 设置、赋值和回读验证

- `spawn_actor_with_defaults`
  - 输入：class、transform、actor/root component 默认值
  - 价值：减少“创建 -> 再设属性 -> 再回读”链路

### 下一批建议

- `create_three_point_lighting`

## Asset

### 已实现

- `query_assets_summary`
  - 返回：失败时不再谎报 `verification=true`，并统一包含 `summary / filters / items`
- `ensure_asset_with_properties`
- `create_asset_with_properties`
- `import_texture_asset`
- `import_fbx_asset`
- `update_asset_properties`

### 后续可长出的命令

- `duplicate_asset_with_overrides`
- `ensure_folder`
- `move_asset_batch`

当前状态：以上三项已实现。

## Material

### 已实现

- `create_material_asset`
- `create_material_instance_asset`
- `update_material_instance_properties`
- `update_material_instance_parameters_and_verify`

说明：

- 这里只覆盖材质资产和材质实例
- 不把复杂材质图编辑放进这个域
- 参数批量更新命令已包含写入与验证

## Material Graph

### 已实现

- `create_material_graph_recipe`
- `connect_material_nodes`
- `analyze_material_graph`

说明：

- 这是独立图编辑域
- 当前已进入最小可用阶段
- 后续会和 `unreal-material` 分开维护

## Diagnostics

### 已实现

- `get_harness_health`
- `route_harness_task`
- `get_domain_design`
- `get_token_usage_summary`

## 进入高层命令的判断标准

满足下面至少两条时，值得提炼成高层命令：

- 同类任务重复出现
- 用户自然语言表达明显强于底层属性表达
- 底层操作容易忘参数或犯错
- 完成后必须带回读验证
- 跨多个底层步骤才能完成

## 后续增强要求

所有高层命令后续都应逐步补上：

- 结构化回执
- `post_state`
- `verification.checks`
- 对应批量版本的 `summary + items` 返回结构
