---
name: ue-harness
description: Use when working inside `D:\unreal-mcp` on Unreal harness code, MCP tool behavior, orchestrator or domain backends, diagnostics, or the `RenderingMCP/Plugins/UnrealMCP` plugin. Covers domain selection, default MCP entrypoints, backend boundaries, and the required execution and validation order for material and material-graph tasks.
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

1. `docs/inventory.md`
2. `docs/categories.md`
3. The domain files for the current task

Read these only when needed:

4. `docs/commands.md`
5. `docs/test-plan.md`
6. `docs/verification.md`
7. `docs/workflow.md`

## Default Entry

1. Classify the task domain first: `scene / asset / material / material_graph / diagnostics`
2. Prefer `unreal_orchestrator` as the default MCP entry
3. Before high-risk live-editor operations, check:
   - `get_editor_ready_state`
   - `wait_for_editor_ready` when needed
4. Enter a domain harness directly only when orchestrator does not already cover the task
5. Treat `unreal_backend_tcp` as internal backend or fallback, not as the default business entrypoint

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
- Treat `python_exec.py`, `commandlet_exec.py`, `unreal_orchestrator/server.py`, `unreal_orchestrator/catalog.py`, and `pyproject.toml` as shared core files; change them only when necessary

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
