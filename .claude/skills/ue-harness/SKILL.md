---
name: ue-harness
description: Use when working inside `D:\unreal-mcp` on Unreal harness code, MCP tool behavior, orchestrator or domain backends, diagnostics, material reconstruction planning, Unity-to-UE migration, or the `RenderingMCP/Plugins/UnrealMCP` plugin. Covers domain selection, default MCP entrypoints, backend boundaries, material execution rules, and migration workflows.
---

# UE Harness

## Purpose

Use this skill for Unreal-side work in this repo.

Default scope:

- `unreal_orchestrator`
- `unreal_scene`
- `unreal_asset`
- `unreal_material`
- `unreal_material_graph`
- `unreal_diagnostics`
- `RenderingMCP/Plugins/UnrealMCP`

## Read First

Read in this order:

1. `inventory.md`
2. `categories.md`
3. The domain files for the current task

Read these only when needed:

4. `commands.md`
5. `test-plan.md`
6. `verification.md`
7. `workflow.md`
8. `mcp-tool-gap-workflow.md`

## Default Entry

1. Classify the task domain first: `scene / asset / material / material_graph / diagnostics`
2. Each domain server (`unreal_<domain>/server.py`) now exports a `TOOLS` list with editor-guarded tools and can run standalone
3. For multi-server clients, prefer connecting to domain servers directly (see `config/mcp_config.multi-server.example.json`)
4. The `unreal_orchestrator` exposes only 3 routing/discovery tools — connect to domain servers directly for domain-specific work
5. Before high-risk live-editor operations, check:
   - `get_editor_ready_state`
   - `wait_for_editor_ready` when needed
6. Enter a domain harness directly when you need only one domain's tools and want to reduce the MCP tool list size
7. Treat `unreal_backend_tcp` as internal backend or fallback, not as the default business entrypoint

## Backend Boundaries

- `scene`
  - prefer live-editor Python
- `asset create/update`
  - prefer live-editor Python
- `asset import`
  - prefer commandlet
- `material_graph`
  - currently still depends on the internal backend and UE plugin C++ commands
- `unreal_backend_tcp`
  - owns TCP transport, raw command dispatch, and large-result handles

## General Rules

- Prefer high-level tools over ad hoc property writes
- Do not mix `material` responsibilities with `material_graph` responsibilities
- Treat `python_exec.py`, `commandlet_exec.py`, `unreal_harness_runtime/editor_guard.py`, `unreal_orchestrator/server.py`, `unreal_orchestrator/catalog.py`, and `pyproject.toml` as shared core files; change them only when necessary

## MCP Tool Gap Workflow

Use this whenever a real user workflow needs `run_python`, raw backend commands, local Python imports, or manual editor/source inspection because the high-level MCP surface is missing, incomplete, unstable, or unverifiable.

1. Finish the user task with a safe fallback when possible.
2. Decide whether the fallback is a repeatable MCP gap using `mcp-tool-gap-workflow.md`.
3. If it is a gap, append a concrete item to `mcp-tool-gap-checklist.md`.
4. Include domain, affected tool, current behavior, fallback used, expected behavior, proposed tool contract, and verification target.
5. Do not record one-off grep/source reading/build/test operations as MCP gaps.

## Engine Source Resolution

Use these rules before reading Unreal Engine source to explain a node, pin, asset type, shader path, or editor behavior.

1. Resolve the active engine first:
   - Run `python scripts/resolve_unreal_engine.py` from the repo root, or read `unreal_harness_runtime.config.get_runtime_paths()`
   - Prefer `UE_ENGINE_ROOT` when explicitly set
   - Then prefer the engine derived from `UE_EDITOR_EXE` or `UE_EDITOR_CMD`
   - Then resolve `UE_PROJECT_PATH` -> `.uproject` `EngineAssociation` via registered Unreal builds
   - Fall back only to candidates in `unreal_harness_runtime/config.py`
2. Treat the resolved `engine_root` as the directory named `Engine`, not the install parent.
3. Verify `engine_source` exists before citing source. If `engine_root_source_available=false`, state that engine source is not available locally.
4. Do not use generated `.sln` paths as the primary authority; they can be stale after switching engines. Use them only as a last-resort clue.
5. Search source in this order:
   - project `Source/` and project `Plugins/`
   - repo plugin `RenderingMCP/Plugins/UnrealMCP/Source/`
   - resolved engine `Source/`
   - resolved engine `Plugins/`
   - resolved engine `Content/Functions/` for material functions
6. When behavior depends on engine code, include the engine path used in the answer or notes.

Useful source targets:

- Material nodes: search `UMaterialExpression<Name>` under `Engine/Source/Runtime/Engine`
- Blueprint nodes: search `UK2Node_<Name>` and `K2Node_<Name>` under `Engine/Source/Editor` and `Engine/Source/Runtime`
- Niagara nodes: search `UNiagaraNode<Name>` under `Engine/Plugins/FX/Niagara`
- Material functions: search `.uasset` names under `Engine/Content/Functions`

## Material Execution

Use these rules whenever the task touches `material` or `material_graph`.

### Function Strategy

- Check for an existing project-local `MaterialFunction` before creating a new one
- Then check engine-provided material functions or a standard UE node pattern
- Create a new function only after confirming there is no reusable implementation
- Split by semantic boundary or source subgraph, not by tiny arithmetic steps
- Do not create micro-functions for `OneMinus`, `Multiply`, `Lerp`, or simple pass-through wiring
- Prefer native UE material nodes inside a function
- Use `Custom` only when the source already uses a custom function or UE node coverage is clearly insufficient
- Keep `Custom` inline
- Do not write `.ush`
- Do not use `include`
- Do not define local helper functions inside the `Custom` snippet

### Build Order

1. Verify editor readiness
2. Verify source package and runtime evidence completeness
3. Import or bind textures
4. Create or refresh material functions
5. Validate each high-risk function individually
6. Create or rebuild the parent material
7. Connect one high-risk branch at a time
8. Re-read and validate after each high-risk branch
9. Do visual inspection only after structural validation passes

### Required Validation

- Build functions before the parent material, and build material instances last
- If a `MaterialFunction` is deleted and recreated, rebuild the parent material or at least rebuild the affected `MaterialFunctionCall`
- Do not keep appending nodes onto a dirty half-finished parent material; rebuild high-risk branches cleanly
- Add an explicit switch parameter for runtime-dependent branches
  - example: `UseDissolve`
  - default values should keep the material visible and debuggable in UE preview
- Write UE parameter `group` values and verify them on readback
- For functions with internal texture sampling or runtime-space dependencies, require a minimal closed loop:
  - function readback is correct
  - parent material compiles
  - structure readback matches expectation
- After graph edits, do not trust `success: true` alone
  - re-read the graph
  - inspect key `property_connections`
  - inspect logs for `Missing Material Function`, shader asserts, or compile fallback
- If visual parity depends on external runtime state, do not claim alignment until that runtime state is present in the source package

### Stop Conditions

Stop and fix tooling or export before continuing if any of the following occur:

- readback is missing expected nodes, functions, or property connections
- the material only compiles by disabling the branch under reconstruction
- `Missing Material Function` appears
- a shader assert appears
- the editor crashes
- a verification report regresses compared with the last successful checkpoint

### Alignment Claims

Do not claim "aligned with source" without a machine-readable verification artifact that checks:

- source evidence completeness
- UE graph structure completeness
- key material property alignment
- parameter group alignment

## Delivery Check

- Confirm the touched files stay within the intended domain
- State whether the editor or plugin must be restarted or rebuilt
- Record known limitations
- Complete at least one real regression, or state clearly why it was not completed

## Additional Resources

- For material reconstruction planning from exported packages: [material-reconstruction.md](material-reconstruction.md)
- For Unity-to-UE scene and lighting migration: [unity-to-ue.md](unity-to-ue.md)
