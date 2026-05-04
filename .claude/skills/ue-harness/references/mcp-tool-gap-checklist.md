# MCP 工具缺口检查清单（Tool Gap Checklist）

> **Language convention**: gap entries use English fields to match MCP tool names and code identifiers. Framework instructions are in Chinese.

Agent 在完成真实 Unreal 任务时发现的 MCP 能力缺口记录在此文件。

在"待处理条目"下追加新条目。保持每条足够具体，使其他 agent 可以稍后实现和验证。

条目实现后标记 `Status: done`，添加验证说明，移至"已完成条目"。不要删除已完成条目。

## 待处理条目

暂无待处理条目。

## 已完成条目

### GAP-0001: Patch existing material expression properties

- Status: done
- Priority: P1
- Domain: material_graph
- Affected tool: `patch_material_graph`
- Workflow: Update a duplicated material graph so an existing `TextureCoordinate` expression changes `coordinate_index` from 1 to 2 without rebuilding the full graph.
- Current behavior: The high-level graph tools expose create, connect, delete, and property-connection operations, but do not expose a direct way to patch editor properties on an existing material expression identified by node id/name/class.
- Fallback used: `run_python` through `unreal_harness_runtime.python_exec`, traversing `MaterialEditingLibrary` graph inputs and calling `set_editor_property("coordinate_index", 2)`.
- Expected behavior: MCP should update an existing material expression property, save/recompile the material, and verify the property readback.
- Proposed tool contract: Extend `patch_material_graph` with `update_nodes: [{ "node_id" | "node_name", "properties": { ... } }]`, or add `set_material_node_property(asset_path, node_selector, properties, compile, save)`.
- Verification: Duplicate `/Game/PVFeature/TA/Materials/M_SPOM_Shell_UV1` to `M_SPOM_Shell_UV2`, update only `MaterialExpressionTextureCoordinate_1.coordinate_index` to `2`, then analyze/read back that UV0 remains coordinate 0 and metadata coordinate is 2.
- Root cause: High-level material graph patch surface lacks existing-node editor-property mutation.
- Notes: Implemented via `patch_material_graph.update_nodes` and backend `build_material_graph.update_nodes`; verified with contract tests, Python compileall, and `RenderingMCPEditor` build. Live asset regression target remains `/Game/PVFeature/TA/Materials/M_SPOM_Shell_UV2` after reloading the updated plugin.

### GAP-0002: Set material override on existing scene StaticMeshComponent

- Status: done
- Priority: P1
- Domain: scene
- Affected tool: `apply_scene_actor_batch`
- Workflow: Assign a material instance to slot 0 of an existing `StaticMeshComponent` on a placed actor without respawning the actor.
- Current behavior: Scene tools expose actor placement, targeting, light recipes, and queries, but no clear high-level command for setting component material overrides on existing actors.
- Fallback used: `run_python` through `unreal_harness_runtime.python_exec`, iterating actors/components and calling `StaticMeshComponent.set_material(0, material)`.
- Expected behavior: MCP should set component material overrides by actor label/name, component selector, and material slot, with readback verification.
- Proposed tool contract: Add `set_actor_component_material(actor_name_or_label, component_name?, material_slot, material_asset_path, save_level?)`, or extend `apply_scene_actor_batch` with a `material_overrides` operation for existing actors.
- Verification: In `/Game/RCF/Maps/Test/Trace/DemoTest`, set `TessellationTestCube_SPOMShell2.StaticMeshComponent0` slot 0 to `/Game/PVFeature/TA/Materials/M_SPOM_Shell_UV2_Inst` and verify `get_material(0)` returns that instance.
- Root cause: High-level scene harness lacks material override operation for existing components.
- Notes: Implemented via `set_actor_component_material` plus `apply_scene_actor_batch.material_overrides`; verified with contract tests, Python compileall, and `RenderingMCPEditor` build. Live level regression target remains `/Game/RCF/Maps/Test/Trace/DemoTest` after reloading the updated plugin.

## 条目模板

```markdown
### GAP-0000: 简短标题

- Status: open
- Priority: P1
- Domain: asset / material_graph / blueprint / scene / niagara / diagnostics / renderdoc
- Affected tool: `tool_name`
- Workflow: 用户试图完成什么工作
- Current behavior: MCP 做了什么或缺少什么能力
- Fallback used: `run_python` / raw command / 本地导入 / 手动编辑器或源码检查
- Expected behavior: MCP 工具应提供什么
- Proposed tool contract: 新工具或参数/结果变更
- Verification: 具体测试、资产路径、图操作或真实回归
- Root cause: 已知详情，或写 `unknown`
- Notes: 可选
```

## 状态值

- `open`：需要实现
- `in_progress`：正在实现中
- `done`：已实现并验证
- `wontfix`：有意不实现，需注明原因

## 维护规则

- 使用下一个顺序 `GAP-0000` 编号
- 待处理条目下只保留 `open` 或 `in_progress` 的条目
- 不要删除已完成条目；标记 `done` 并移至已完成条目
- 实现后在 Notes 中链接 commit 或测试
- 不相关的能力拆分为独立条目
- 重复条目通过向旧条目追加证据来合并
