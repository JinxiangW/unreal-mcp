# MCP 工具缺口检查清单（Tool Gap Checklist）

> **Language convention**: gap entries use English fields to match MCP tool names and code identifiers. Framework instructions are in Chinese.

Agent 在完成真实 Unreal 任务时发现的 MCP 能力缺口记录在此文件。

在"待处理条目"下追加新条目。保持每条足够具体，使其他 agent 可以稍后实现和验证。

条目实现后标记 `Status: done`，添加验证说明，移至"已完成条目"。不要删除已完成条目。

## 待处理条目

### GAP-0005: Account for implicit connection removal when deleting material nodes

- Status: open
- Priority: P2
- Domain: material_graph
- Affected tool: `patch_material_graph`
- Workflow: Delete a material node that owns an existing node-to-node connection while also replacing material root property connections.
- Current behavior: The backend correctly deletes the node and its incident connections, and readback is correct, but high-level delta verification expects the pre-delete node connection count unless the caller also lists each incident edge in `disconnect_connections`. The tool therefore reports `success: false` for a successful patch.
- Fallback used: Trust the verified post-operation graph readback after confirming node count and `property_connections`.
- Expected behavior: Deleting a node should account for its incident node connections during post-connection-count verification, without requiring redundant `disconnect_connections` entries.
- Proposed tool contract: Update `_run_graph_patch` verification to resolve deleted node selectors against the pre-graph and subtract incident node connections, or omit the exact connection-count check when deletion selectors are present and rely on structural readback.
- Verification: On `/Game/PVFeature/TA/EditorTools/POMBaker/Materials/M_ShallowPudPOM`, delete `BreakMaterialAttributes`, disconnect nine legacy root properties, and add `MaterialAttributes`; expect one node, zero node connections, one `MaterialAttributes` property connection, and overall `success: true`.
- Root cause: High-level delta verification does not include connections implicitly removed by `delete_nodes`.

## 已完成条目

### GAP-0006: Skeletal FBX commandlet import options

- Status: done
- Priority: P1
- Domain: asset
- Affected tool: `import_fbx_asset`
- Workflow: Import a Unity/Endfield skeletal character FBX with custom import rotation, no material/texture import, split skeletal hierarchy meshes, and stable commandlet execution instead of live editor import.
- Current behavior: `import_fbx_asset` already used the commandlet backend, but forced `import_as_skeletal=False` and exposed no FBX import options, so skeletal character imports still required ad hoc UE Python commandlet scripts.
- Fallback used: Temporary UE commandlet scripts constructing `unreal.FbxImportUI` manually for Laevat staging imports and rotation probes.
- Expected behavior: MCP should route static and skeletal FBX imports through the isolated commandlet and expose the required FBX import options directly.
- Proposed tool contract: Extend `import_fbx_asset` with `destination_name`, `import_as_skeletal`, material/texture/animation flags, `import_rotation`, static `combine_meshes`, skeletal hierarchy/skeleton/physics options, and common FBX import data flags.
- Verification: `uv run python -m unittest tests.test_contracts` passed; `uv run python -m py_compile commandlets\\asset_import_commandlet.py unreal_asset\\tools.py tests\\test_contracts.py` passed; `save=False` MyToon commandlet smoke import of Laevat skeletal FBX to `/Toon/Render/Models/__MCPCommandletSmoke` succeeded with 4 imported object paths, no warnings, and `exit_code=0`; no smoke-test `.uasset` files were persisted.
- Root cause: The high-level asset import contract was narrower than the existing commandlet backend and covered only static FBX defaults.

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
- Notes: Implemented via `patch_material_graph.update_nodes` and backend `build_material_graph.update_nodes`; verified with contract tests, Python compileall, Main_Client build/load, and a synthetic Main_Client live regression under `/Game/MCPTest/MaterialGraphBackend`. No SPOM assets were touched for this regression.

### GAP-0003: Material graph backend readback parity for custom outputs and property connections

- Status: done
- Priority: P1
- Domain: material_graph
- Affected tool: `create_material_graph_recipe`, `patch_material_graph`, `analyze_material_graph`
- Workflow: Create a material function with an inline `Custom` node that exposes additional outputs, call it from a parent material, connect material root properties including `PixelDepthOffset`, and verify graph readback after function refresh, disconnect, and delete-node cleanup.
- Current behavior: Before this change, `Custom.additional_outputs`, resolved `MaterialFunctionCall` pins, `TransformPosition` spaces, `TextureCoordinate.coordinate_index`, and `PixelDepthOffset` property readback were incomplete or easy to desynchronize when mixed with UE Python graph editing.
- Fallback used: None for the final workflow. The accepted boundary is Python MCP/TCP wrapper plus C++ material graph backend; no UE Python `MaterialEditingLibrary` graph wiring fallback.
- Expected behavior: MCP graph tools create, patch, connect, disconnect, delete, and read back material graph structure through the C++ backend, with property readback matching write/delete support.
- Proposed tool contract: Keep `create_material_function_asset` for function asset creation, then use `create_material_graph_recipe`, `patch_material_graph`, `set_material_graph_property_connections`, and `analyze_material_graph` for graph operations.
- Verification: Contract tests passed; `compileall` passed; `git diff --check` passed; Main_Client live regression passed with 27 checks using only temporary assets under `/Game/MCPTest/MaterialGraphBackend`, then deleted those assets and confirmed the folder was empty.
- Root cause: C++ backend readback and cleanup coverage lagged behind graph write support, while UE Python graph editing had stale pin and material property synchronization risks.
- Notes: `MaterialFunctionCall` output order should not be hard-coded. Use named `source_output` values when building; readback returns resolved `Output_N` pins.

### GAP-0004: Direct Material Attributes root property connections

- Status: done
- Priority: P1
- Domain: material_graph
- Affected tool: `set_material_graph_property_connections`, `patch_material_graph`, `analyze_material_graph`
- Workflow: Connect a `MaterialFunctionCall` Material Attributes output directly to a parent material root with `bUseMaterialAttributes=true`, without inserting `BreakMaterialAttributes` and reconnecting every individual property.
- Current behavior: The backend supported individual material properties and `PixelDepthOffset`, but omitted hidden `MP_MaterialAttributes` from the supported-property list, name mapping, and graph readback.
- Fallback used: A temporary `BreakMaterialAttributes` node plus individual root property connections.
- Expected behavior: Accept `MaterialAttributes` or `material_attributes` in property connection requests and return the direct root connection during graph readback.
- Proposed tool contract: Extend the existing material root `property_connections` contract with `MaterialAttributes` mapped to `MP_MaterialAttributes`.
- Verification: Live Coding loaded the updated UnrealMCP module; `/Game/PVFeature/TA/EditorTools/POMBaker/Materials/M_ShallowPudPOM` was converted to one `MaterialFunctionCall`, zero node connections, and one `MaterialAttributes` root connection. Readback verified `use_material_attributes=true`; the parent material and `/Game/PVFeature/TA/EditorTools/POMBaker/Materials/MI_ShallowPudPOM_BP_pond_01` compiled for PCD3D_SM6 without material errors after correcting the PackedRMAO default sampler pairing. `uv run --with pytest pytest -q` passed 65 tests.
- Root cause: `MP_MaterialAttributes` was missing from `SupportedMaterialPropertyNames`, `GetMaterialPropertyInput`, and material graph property readback.
- Notes: Loaded through `UnrealEditor-UnrealMCP.patch_0`; a normal editor restart will load the rebuilt base module after the plugin is rebuilt outside Live Coding.

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
- Notes: Implemented via `set_actor_component_material` plus `apply_scene_actor_batch.material_overrides`; verified with contract tests and Python compileall. Live level regression target remains `/Game/RCF/Maps/Test/Trace/DemoTest` after reloading the updated plugin.

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
