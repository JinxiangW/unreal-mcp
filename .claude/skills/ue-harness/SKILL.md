---
name: ue-harness
description: Use when working inside `D:\unreal-mcp` on Unreal harness code, MCP tool behavior, orchestrator or domain backends, diagnostics, material reconstruction planning, Unity-to-UE migration, or the `RenderingMCP/Plugins/UnrealMCP` plugin. Covers domain selection, default MCP entrypoints, backend boundaries, material execution rules, and migration workflows.
---

# UE Harness

> **Language convention**: conceptual overviews and background are in Chinese. Operational instructions (build orders, stop conditions, validation rules, checklists) are in English to match code identifiers and MCP tool names. Key bilingual terms are noted on first use.

## 用途

在 `D:\unreal-mcp` 仓库内处理 Unreal 相关工作时的默认 skill。

覆盖范围（Scope）：

- `unreal_orchestrator` — 路由与发现
- `unreal_scene` — 场景与关卡编辑
- `unreal_asset` — 资产管理
- `unreal_material` — 材质资产工作流
- `unreal_material_graph` — 材质图（Material Graph）编辑
- `unreal_diagnostics` — 诊断
- `RenderingMCP/Plugins/UnrealMCP` — UE 侧 C++ 插件

## 阅读顺序

1. `inventory.md` — 功能清单与状态矩阵
2. `categories.md` — 分层分域索引与故障路由
3. 当前任务对应域的文件
4. （需要时）`commands.md` `test-plan.md` `verification.md` `workflow.md`
5. （需要时）`mcp-tool-gap-workflow.md`

## 默认入口

1. 先判断任务所属域（domain）：`scene / asset / material / material_graph / diagnostics`
2. Default entry: `unreal_mcp/server.py` — 统一聚合所有域工具（~80 tools），自带 editor guard
3. 各域 `server.py` 可独立运行（仅按需调试时使用）
4. `unreal_orchestrator` exposes only 3 routing/discovery tools — optional, for task routing
5. Before high-risk live-editor operations, check:
   - `get_editor_ready_state`
   - `wait_for_editor_ready` when needed
6. `unreal_backend_tcp` is an internal backend / fallback — not a default business entrypoint

## Backend 边界

- **scene**：prefer live-editor Python
- **asset create/update**：prefer live-editor Python
- **asset import**：prefer commandlet（命令行导入）
- **material_graph**：currently depends on internal backend and UE plugin C++ commands
- **unreal_backend_tcp**：owns TCP transport, raw command dispatch, and large-result handles

## 通用规则

- Prefer high-level tools over ad hoc property writes
- Do not mix `material` responsibilities with `material_graph` responsibilities
- 共享核心文件（shared core files，只在必要时修改）：`python_exec.py` `commandlet_exec.py` `unreal_harness_runtime/editor_guard.py` `unreal_orchestrator/server.py` `unreal_orchestrator/catalog.py` `pyproject.toml`

## MCP 工具缺口流程（Tool Gap Workflow）

真实用户工作流因高层 MCP 能力缺失、不完整或不可验证而需要走 fallback 时使用。

1. Finish the user task with a safe fallback when possible
2. Use `mcp-tool-gap-workflow.md` to decide whether the fallback is a repeatable MCP gap
3. If it is a gap, append a concrete item to `mcp-tool-gap-checklist.md`
4. 条目需包含：domain, affected tool, current behavior, fallback used, expected behavior, proposed tool contract, verification target
5. Do not record one-off grep/source reading/build/test operations as MCP gaps

## 引擎源码定位（Engine Source Resolution）

在阅读 Unreal Engine 源码来解释节点、引脚、资产类型、shader 路径或编辑器行为时使用。

1. Resolve the active engine first:
   - Run `python scripts/resolve_unreal_engine.py` from repo root, or read `unreal_harness_runtime.config.get_runtime_paths()`
   - Prefer `UE_ENGINE_ROOT` when explicitly set
   - Then prefer engine derived from `UE_EDITOR_EXE` or `UE_EDITOR_CMD`
   - Then resolve `UE_PROJECT_PATH` → `.uproject` `EngineAssociation` via registered Unreal builds
   - Fall back only to candidates in `unreal_harness_runtime/config.py`
2. Treat resolved `engine_root` as the directory named `Engine`, not the install parent
3. Verify `engine_source` exists before citing source. If `engine_root_source_available=false`, state that engine source is not available locally
4. Do not use generated `.sln` paths as primary authority — they can be stale after switching engines
5. Search source in this order:
   - project `Source/` and project `Plugins/`
   - repo plugin `RenderingMCP/Plugins/UnrealMCP/Source/`
   - resolved engine `Source/`
   - resolved engine `Plugins/`
   - resolved engine `Content/Functions/` (for material functions)
6. When behavior depends on engine code, include the engine path used in the answer or notes

常用源码目标（Useful source targets）：

- Material nodes: search `UMaterialExpression<Name>` under `Engine/Source/Runtime/Engine`
- Blueprint nodes: search `UK2Node_<Name>` and `K2Node_<Name>` under `Engine/Source/Editor` and `Engine/Source/Runtime`
- Niagara nodes: search `UNiagaraNode<Name>` under `Engine/Plugins/FX/Niagara`
- Material functions: search `.uasset` names under `Engine/Content/Functions`

## 材质执行（Material Execution）

涉及 `material` 或 `material_graph` 时使用以下规则。操作性指令（build order, validation, stop conditions）使用英文以匹配 MCP 工具名和代码标识符。

### 函数策略（Function Strategy）

概念指引（中文）：

- 新建 `MaterialFunction` 前先检查是否已有项目本地版本，再检查引擎提供的材质函数或标准 UE 节点模式
- 按语义边界或源码子图拆分，不要按细碎的算术步骤
- 不要为 `OneMinus` `Multiply` `Lerp` 或简单直连创建微函数
- 函数内部优先使用原生 UE material node
- `Custom` 仅用于确实缺原生节点或源码本来就是自定义逻辑的场景

Operational rules:

- Check for an existing project-local `MaterialFunction` before creating a new one
- Then check engine-provided material functions or a standard UE node pattern
- Create a new function only after confirming there is no reusable implementation
- Split by semantic boundary or source subgraph, not by tiny arithmetic steps
- Do not create micro-functions for `OneMinus`, `Multiply`, `Lerp`, or simple pass-through wiring
- Prefer native UE material nodes inside a function
- Use `Custom` only when the source already uses a custom function or UE node coverage is clearly insufficient
- Keep `Custom` inline — do not write `.ush`, do not use `include`, do not define local helper functions inside the `Custom` snippet

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
  - Example: `UseDissolve`
  - Default values should keep the material visible and debuggable in UE preview
- Write UE parameter `group` values and verify them on readback
- For functions with internal texture sampling or runtime-space dependencies, require a minimal closed loop:
  - function readback is correct
  - parent material compiles
  - structure readback matches expectation
- After graph edits, do not trust `success: true` alone:
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

## 交付检查（Delivery Check）

- Confirm the touched files stay within the intended domain
- State whether the editor or plugin must be restarted or rebuilt
- Record known limitations
- Complete at least one real regression, or state clearly why it was not completed

## 附加资源（Additional Resources）

- 材质重建规划（Material Reconstruction Planning）：[material-reconstruction.md](material-reconstruction.md)
- Unity 到 UE 场景与灯光迁移：[unity-to-ue.md](unity-to-ue.md)
