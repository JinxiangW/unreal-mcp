# 第一批高层命令清单

这份文档定义当前值得沉淀成高层命令的第一批工作流。

原则：

- 先覆盖高频、容易犯错、需要领域语义的任务
- 不把所有底层能力都包装成高层命令
- 高层命令随真实使用逐步增长

## Scene

### 已开始实现

- `set_scene_light_intensity`
  - 输入：actor、intensity、unit、mobility
  - 价值：避免只写 `Intensity` 忘记单位

- `create_spot_light_ring`
  - 输入：center、radius、z、count、target、intensity、unit、mobility
  - 价值：把批量摆灯、朝向、单位、可移动性收成一个配方

### 下一批建议

- `aim_actor_at`
- `set_post_process_overrides`
- `spawn_actor_with_defaults`
- `create_three_point_lighting`

## Asset

### 第一批建议

- `create_asset_with_properties`
- `import_texture_asset`
- `import_fbx_asset`
- `update_asset_properties`

### 后续可长出的命令

- `duplicate_asset_with_overrides`
- `ensure_folder`
- `move_asset_batch`

## Material

### 第一批建议

- `create_material_asset`
- `create_material_instance_asset`
- `update_material_instance_properties`

说明：

- 这里只覆盖材质资产和材质实例
- 不把复杂材质图编辑放进这个域

## Material Graph

### 第一批建议

- `create_material_graph_recipe`
- `connect_material_nodes`
- `analyze_material_graph`

说明：

- 这是独立图编辑域
- 后续会和 `unreal-material` 分开维护

## Diagnostics

### 第一批建议

- `get_harness_health`
- `route_harness_task`
- `get_domain_design`

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
