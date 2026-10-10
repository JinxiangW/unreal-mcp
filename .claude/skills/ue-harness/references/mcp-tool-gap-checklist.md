# MCP 工具缺口检查清单（Tool Gap Checklist）

> **Language convention**: gap entries use English fields to match MCP tool names and code identifiers. Framework instructions are in Chinese.

Agent 在完成真实 Unreal 任务时发现的 MCP 能力缺口记录在此文件。

在"待处理条目"下追加新条目。保持每条足够具体，使其他 agent 可以稍后实现和验证。

条目实现后标记 `Status: done`，添加验证说明，移至"已完成条目"。不要删除已完成条目。

## 待处理条目

### GAP-0008: Patch Custom input arrays without partial graph mutation

- Status: open
- Priority: P1
- Domain / affected tool: material_graph / `patch_material_graph`
- Workflow: Extend `/Game/FX_lightfuncTest` Custom expression with a connected `offsetCM` input while retaining its five existing inputs.
- Current behavior: `update_nodes.properties.Inputs` fails with `Unsupported property type: ArrayProperty`; nodes and scalar properties earlier in the same patch have already been applied.
- Fallback used: MCP editor Python appends `unreal.CustomInput`, preserving existing input structs, followed by native graph connections and independent readback.
- Expected behavior / proposed contract: Add typed Custom-input append/update support and validate all unsupported updates before creating nodes; preserve existing links by input name.
- Verification: Six named connected inputs, original five links intact, no duplicate added nodes after failure/retry, successful SM6 compilation. Evidence: `E:/capture-tool/ue-caustics/material_patch.result.json`, `readback.result.json`.

### GAP-0009: Count replaced material connections by destination input

- Status: open
- Priority: P2
- Domain / affected tool: material_graph / `patch_material_graph`
- Workflow: Reconnect existing Custom inputs alongside new graph connections in `/Game/FX_lightfuncTest`.
- Current behavior: Native patch creates/sets 40 links, five replace existing links. High-level verification expects 7+40=47 links and reports failure; independent graph correctly has 42.
- Fallback used: Verify unique source/target/input/output tuples and six Custom inputs on independent readback, then perform actual UE rendering checks.
- Expected behavior / proposed contract: Account for replacement/idempotent connections keyed by destination node and input instead of always adding the requested count.
- Verification: Reapplying an identical link is successful and does not increase total links. Evidence: `E:/capture-tool/ue-caustics/connect_patch.result.json`, `validation_report.json`.


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
### GAP-0015: Create and verify real material static-switch permutations

- Status: done
- Priority: P1
- Domain / affected tools: material_graph / `ensure_material_static_switch_inputs`; material / `set_material_instance_static_switches`.
- Workflow: Build four inverse-L1 impostor permutations with `UseHierarchy` and `UseBilinear`, without runtime scalar branches pretending to be compile-time switches.
- Previous behavior: Native graph recipe lacks StaticSwitchParameter creation; the high-level instance updater does not handle static values.
- Implemented contract: Create/reuse native StaticSwitchParameter expressions with True/False inputs, connect to existing named inputs, compile/save and verify graph links. Batch native instance overrides, update the permutation once, save and read back.
- Engine detail: UE 5.6 `MaterialEditingLibrary.cpp::SetMaterialInstanceStaticSwitchParameterValue` writes the value but always returns false. The wrapper preflights names and validates native readback instead of relying on that return value.
- Verification: Four live `MI_OR_Rho_*` instances under `/Game/PVFeature/TA/FrostedGlass/TrueImposter/OctaRadial`, different compiled shader statistics, exact switch readback, CPU/GPU intersection fixtures. Unit tests cover the false return, bool validation, unknown names and failed graph verification.

### GAP-0014: Texture Object sampler properties were ignored and omitted from readback

- Status: done
- Priority: P1
- Domain / affected tool: material_graph / texture object recipe creation and sampler inspection.
- Workflow: Linear depth, packed UV, Bounds and RMO TextureObjectParameters displayed Color sampler warnings.
- Root cause: Native texture object creation did not apply the supplied sampler type; native graph output omitted the property, hiding the mismatch.
- Implemented contract: `sync_material_texture_samplers(material_path, repair=False)` inspects actual TextureBase properties, derives sampler requirements from compression/sRGB/data-group/VT settings, and optionally repairs, recompiles, saves and reads back. LayerStudy builders call this after graph creation.
- Verification: Live `/Game/PVFeature/TA/FrostedGlass/TrueImposter/LayerStudy` four masters; 11 mismatches repaired. Unit regression executes generated code with a TextureObjectParameter analogue and checks read-only, repair and idempotence behavior.
- Related limitation: Updating a node's texture via native `update_nodes` rejects ObjectProperty. Existing delete/create/reconnect graph operations safely replace that one node without rebuilding the material.

### GAP-0013: Native texture arrays, authored mips and exact GPU data readback

- Status: done
- Priority: P1
- Domain / affected tool: asset / `import_texture_arrays`, `inspect_texture_arrays`; scene / `render_material_data`, `render_static_mesh_preview`
- Workflow: Import depth/UV arrays with 18/36 slices and conservative Bounds with 3 slices and 9 authored mips; validate actual GPU values for an opaque impostor.
- Previous behavior / fallback: Batch import had no DDS array contract; source DDS export through the native exporter asserted on Texture2DArray. Shader-data and HDR diagnostic readback lacked suitable high-level tools.
- Implemented contract: Checked raw mip files -> correctly ordered DX10 DDS -> isolated native importer, explicit formats/settings and class verification. Safe property/registry inspection replaces unsupported DDS export. Linear material-to-PNG output supports float bit-pattern probes; scene previews additionally support HDR EXR and report actual camera rotation. Canonicalize texture parameter paths before comparison.
- Verification: `/Game/PVFeature/TA/FrostedGlass/TrueImposter/LayerStudy`. Six arrays, all slices, all 22 array/mip combinations: exact R32F/RGBA32F bits and UV bytes on GPU. Twelve-view quality, source-texture replacement, fallback maps and two rounds of GPU CSV captured. 108 Python tests and compileall pass. Existing 26 assets and default material unchanged.
- Evidence: `F:/GFFEngines/Main_Client/Saved/GeneratedAssets/TrueImposter/LayerStudy/reports/final_validation.json`; interface notes: `docs/texture-array-data.md`.
- Recovery: Native `ExportTextureSourceToDDS` assertion was diagnosed; the unsafe call was removed from inspection and the editor was restored. No engine/plugin C++ edits were required.

### GAP-0012: Render and profile a material without desktop interaction

- Precision follow-up (2026-09-15): Added optional `world_origin` (existing default preserved) and origin readback to `render_static_mesh_preview`. OctaRadial diagnostics at Z=-100000 showed 64 CPU/GPU mask differences in one view, versus 7 at the origin; synthetic local GPU ray tests matched. Near-origin and far-origin captures are retained separately. Added validation for finite positions and regression tests for shared mesh/camera translation.

- Status: done
- Priority: P1
- Domain / affected tool: scene / `render_static_mesh_preview`; material / `get_material_statistics`
- Workflow: Validate a custom opaque material against real geometry from multiple views and compare quality-tier GPU costs without computer use.
- Previous behavior / fallback: No high-level isolated preview or compiled-statistics tools; ad hoc editor Python was necessary.
- Implemented contract: Show-only transient mesh capture with manual exposure, PNG readback, guaranteed normal-path cleanup; optional bounded asynchronous GPU CSV profiling with one capture per engine frame and completion/cleanup sidecar. Read native compiled shader statistics independently.
- Verification: `/Game/PVFeature/TA/FrostedGlass/TrueImposter`, twelve-view mask IoU 99.16%-99.61%, rotation/scale checks, five quality tiers profiled, temporary actors destroyed and GPU cvars restored. `Main_Client/Saved/GeneratedAssets/TrueImposter/reports/final_validation.json`.

### GAP-0011: Preserve parameter defaults across readback and graph recipes

- Status: done
- Priority: P1
- Domain / affected tool: material_graph / `create_material_graph_recipe`
- Workflow: Create nonzero scalar/vector parameter defaults for an opaque ray-casting material.
- Previous behavior / fallback: Readback exposes `default_value`, but C++ creation expects `value`; defaults silently became zero and blacked out the material. Manual per-instance parameters could mask the error.
- Implemented contract: Normalize `default_value` to `value` for parameter creation, preserve explicitly supplied `value`, and normalize CameraVectorWS's readback name to its builder name.
- Verification: Unit coverage plus repeated live material rebuilds; all scalar/vector defaults independently compared to the recipe. Five quality tiers render correctly; 103 tests pass.

### GAP-0010: Isolate batch texture/mesh imports from live TaskGraph execution

- Status: done
- Priority: P1
- Domain / affected tool: asset / `import_assets_batch`, `inspect_static_mesh`, `set_static_mesh_material`
- Workflow: Import R32F/RGBA32F layered-depth assets, byte textures and an FBX with settings applied, saved and verified.
- Previous behavior / fallback: Individual commandlet tools lack batch/settings contracts. A trial synchronous live ImportAssetTasks call asserted TaskGraph RecursionGuard during Interchange import and crashed UE.
- Implemented contract: Validate 1-16 inputs, import in an isolated commandlet resolved from the project's engine, apply settings and save/read back each item. Parse both stdout and UE log because Python prints may only appear in the log. Explicit replace_existing is required for overwrites. Mesh tools read geometry counts and save default material references.
- Verification: Two successful commandlet batches in `/Game/PVFeature/TA/FrostedGlass/TrueImposter`; six textures and two meshes; runtime mesh has one Section and 1452 triangles. Editor restored after the trial failure. Unit regressions, compileall and actual rendering passed.

### GAP-0005: Account for implicit connection removal when deleting material nodes

- Status: done
- Priority: P2
- Domain / affected tool: material_graph / `patch_material_graph`
- Workflow: Delete a material node with incident connections while replacing root property connections.
- Previous behavior / fallback: Backend/readback were correct, but delta verification retained pre-delete edges unless they were explicitly disconnected; callers had to verify a falsely failed operation independently.
- Implemented contract: Read the pre-graph when deleting node IDs, subtract incident connections once, and use the actual property_connection_count when post-readback is a summary.
- Verification: Unit deletion/rebuild regression and repeated full rebuilds of `/Game/PVFeature/TA/FrostedGlass/TrueImposter/M_TI_FrostedBox_1` and its quality variants. Correct node/connection/property counts, successful readback and actual rendered images; 103 tests passed on 2026-09-11.
- Original verification target retained for history: `/Game/PVFeature/TA/EditorTools/POMBaker/Materials/M_ShallowPudPOM` delete BreakMaterialAttributes and replace roots with MaterialAttributes. This asset was not modified during the 2026-09-11 regression.

### GAP-0007: Preserve dynamic inputs when renaming particle assignments

- Status: done
- Priority: P1
- Domain: niagara
- Workflow: Replace the duplicate constant `Particles.rad` with the original `Particles.Param` curve and bind Center to a particle's world-space position in an existing system.
- Previous behavior: No native rename or assignment-input binding operation. Rebuilding emitters or using computer interaction is unsuitable; the user explicitly requires MCP for this work.
- Implemented: Assignment inspection, rename preflight/execution preserving override links and rapid iteration values, and Simulation-to-World position binding. Dry runs do not dirty assets. Connected destination overrides and unrelated conflicting writers are rejected.
- Validation: 99 Python tests passed; native C++ compilation/linking and user-controlled reload passed. Live `/Game/NS_LFTest` rename preserved the original curve connection and removed duplicate constants. At 1.5s particle/component/MID radius was 0.5000005364; at 3s it was 0. Center and material LightPosition both matched the actual light world position (1234,567,150). Width=30 and Smoothness=5 were preserved. Evidence: Main_Client `tmp/lf_rename_runtime_result.json` and `tmp/lf_rename_center_result.json`.
- Stability corrections: Newly created read pins are named directly, avoiding editor-only parameter-definition subscription callbacks. Enum pin defaults use member names, not integers. Readback verifies Simulation → World and Apply Scale=true, rather than only checking that a link exists.


### GAP-0016: Niagara Component Renderer property binding creation and readback

- Status: done
- Priority: P1
- Domain: niagara
- Affected tools: `get_niagara_renderers`, `set_niagara_component_binding`
- Workflow: Bind a Niagara float curve to a Blueprint point-light component setter, then update scalar `Param` on its light-function MID.
- Previous behavior: Generic asset Python cannot edit protected `PropertyBindings`; renderer queries omitted bindings. Unconsumed custom attributes can be optimized out, and assignment targets are not always in graph metadata.
- Fallback used: Local Python conversion scripts and attempted UI binding before adding typed native support.
- Implemented contract: Native `set_component_binding` validates editable property, particle dataset/declarations/assignment targets and type conversion; updates one binding with a transaction, recompiles, saves and independently verifies the result. Standalone server: `python -m unreal_niagara.server`.
- Verification: 93 Python tests passed. ClientEditor/UnrealMCP offline build passed. Live `/Game/NS_LFTest`, emitter `LFPointLight`: initial and repeated binding both verified, one `Param` binding retained; missing attribute and Position-to-float rejected. Simulation at 1.5s produced matching particle/component/MID values `0.5000005364`; at 3s and 3.5s all were exactly zero while the light still existed with intensity 5000.
- Related stability fix: Native emitter removal closes associated Niagara asset editors before invalidating handles, uses an editor transaction, then requests compilation. Latest observed crash was a stale stack view model dereferencing an erased emitter handle during Tick. Closed-editor structural removal and subsequent simulation passed; an open-editor stress regression has not been performed.
- Evidence: Main_Client `tmp/lf_mcp_regression.json`, `tmp/lf_verified_fade.json`, `tmp/lf_final_overview.json`. Engine: `F:/GFFEngines/Develop_Maomi/Engine`.

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
