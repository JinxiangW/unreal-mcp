---
name: ue-harness
description: 使用 `unreal-mcp` 时的最小工作指南，覆盖域选择、默认入口、后端边界和测试顺序。
license: MIT
compatibility: opencode
metadata:
  scope: repo-local
  repo: unreal-mcp
---

## Purpose

当任务发生在 `D:\unreal-mcp`，并且涉及 Unreal harness 的实现、扩展、测试或排障时，优先使用这份 skill。

## 先看什么

按顺序：

1. `docs/inventory.md`
2. `docs/categories.md`
3. 当前任务相关的域文件

如果要改行为或架构，再看：

4. `docs/proposal.md`
5. `docs/commands.md`

如果要测试或交付，再看：

6. `docs/test-plan.md`
7. `docs/verification.md`
8. `docs/workflow.md`

## 默认入口

1. 先判定任务域：`scene / asset / material / material_graph / diagnostics`
2. 默认入口优先 `unreal_orchestrator`
3. 高风险 live-editor 命令先做：
   - `get_editor_ready_state`
   - 必要时 `wait_for_editor_ready`
4. 只有 orchestrator 尚未覆盖时，才直接进入对应 domain harness
5. `unreal_backend_tcp` 仅作为内部 backend / fallback，不作为默认业务入口

## 域边界

- `unreal_scene/`
- `unreal_asset/`
- `unreal_material/`
- `unreal_material_graph/`
- `unreal_orchestrator/`
- `unreal_diagnostics/`

## 当前后端边界

- `unreal_backend_tcp`
  - internal / fallback only
  - 负责 TCP transport、raw command、result handle
- `scene`
  - 优先 live editor python
- `asset create/update`
  - 优先 live editor python
- `asset import`
  - 优先 commandlet
- `material_graph`
  - 当前仍通过内部 backend 支撑

## 工作规则

- 优先高层命令，不继续堆裸属性写入
- 不混淆 `material` 和 `material_graph`
- `python_exec.py`、`commandlet_exec.py`、`unreal_orchestrator/server.py`、`unreal_orchestrator/catalog.py`、`pyproject.toml` 属于共享核心文件，修改前先确认必要性

## 交付前自检

- 是否只改了对应域的文件
- 是否说明是否需要重启编辑器或重编插件
- 是否记录已知限制
- 是否至少完成一条真实环境回归或说明未完成原因
