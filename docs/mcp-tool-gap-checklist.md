# MCP Tool Gap Checklist

Use this file for MCP capability gaps discovered while agents complete real Unreal tasks.

Append new items under `Open Items`. Keep each item concrete enough that another agent can implement and verify it later.

## Open Items

### GAP-0001: Patch existing material expression properties

- Status: open
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
- Notes: Discovered while fixing `/Game/PVFeature/TA/Meshes/TessellationTestCube_SPOMShell` whose SPOM metadata is in UV2.

### GAP-0002: Set material override on existing scene StaticMeshComponent

- Status: open
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
- Notes: The task intentionally did not save the level after applying the live-editor material override.

## Item Template

```markdown
### GAP-0000: Short title

- Status: open
- Priority: P1
- Domain: asset / material_graph / blueprint / scene / niagara / diagnostics / renderdoc
- Affected tool: `tool_name`
- Workflow: What the user was trying to do
- Current behavior: What MCP did or failed to expose
- Fallback used: `run_python` / raw command / local import / manual editor/source inspection
- Expected behavior: What the MCP tool should provide
- Proposed tool contract: New tool or parameter/result changes
- Verification: Concrete test, asset path, graph operation, or live regression
- Root cause: known detail, or `unknown`
- Notes: optional
```

## Status Values

- `open`: Needs implementation.
- `in_progress`: Being implemented.
- `done`: Implemented and verified.
- `wontfix`: Intentionally not implemented; include reason.

## Maintenance Rules

- Use the next sequential `GAP-0000` id.
- Do not delete completed items; mark them `done`.
- Link commits or tests in `Notes` after implementation.
- Split unrelated capabilities into separate items.
- Merge duplicates by adding evidence to the older item.
