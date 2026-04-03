---
name: ue-harness
description: 使用 `unreal-mcp` 时的最小工作指南，涵盖域选择、执行后端、静默工作流和交付要求。
license: MIT
compatibility: opencode
metadata:
  scope: repo-local
  repo: unreal-mcp
---

## Purpose
当任务发生在 `D:\ue-mcp\unreal-mcp`，并且涉及 Unreal harness 的实现、扩展、测试或排障时，优先使用这份 skill。

这份 skill 只保留最小必要规则，不重复展开所有长文档。

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
9. `docs/parallel.md`

## 默认执行顺序
如果用户没有特别指定入口，默认按这个顺序执行，不要让用户每次手动决定：

1. 先判断任务域：`scene / asset / material / material_graph / diagnostics`
2. 优先走 `unreal_orchestrator`
3. 如果是高风险 live editor 操作，先做：
   - `get_editor_ready_state`
   - 必要时 `wait_for_editor_ready`
4. 能用 orchestrator 的 guarded 命令，就不要直接打 raw 工具
5. 只有在 orchestrator 还没覆盖该能力时，才直接进入对应域 harness
6. `unreal_editor_mcp` 只作为最后的 internal/fallback 层，不作为默认入口

简单说：

- 默认入口：`unreal_orchestrator`
- 默认预检：`get_editor_ready_state`
- 默认等待：`wait_for_editor_ready`
- 默认禁止：直接优先使用 legacy raw 工具
- 默认禁止：普通使用场景下隐式自动启动编辑器

## 域选择
先按问题域选目录，不要一上来全仓库乱改。

- `scene`: `unreal_scene/`
- `asset`: `unreal_asset/`
- `material`: `unreal_material/`
- `material_graph`: `unreal_material_graph/`
- `orchestrator`: `unreal_orchestrator/`
- `diagnostics`: `unreal_diagnostics/`

## 当前后端边界
- `unreal_editor_mcp`: internal / fallback only，不应继续视为默认业务入口
- `scene`: 优先 `live editor python`
- `asset create/update`: `live editor python`
- `asset import`: `commandlet`
- `material asset/instance/parameter`: 基于新 `asset` / live editor python
- `material_graph`: 仍在拆分，暂时不要混入 `material`

## 当前总控行为
- `unreal_orchestrator` 对部分高风险 live editor 命令已自动做 ready preflight
- 如果任务要走高风险编辑，优先通过 orchestrator，而不是直接盲打底层 raw 工具

## 重试规则
- 只读：最多 3 次
- 幂等写：最多 2 次
- 非幂等写：默认不要自动整条重试
- commandlet：最多补重试 1 次

失败时不要只返回一句报错，至少要保留：

- `operation`
- `attempt`
- `max_attempts`
- `error_type`
- `error_message`
- `recommended_action`

## 工作规则
### 1. 先选对执行模型
- 需要当前关卡/Actor/Viewport：用 live editor
- 导入、大批量无 UI 操作：优先 commandlet

### 2. 不随便改共享核心
同时只能有一个会话改这些文件：

- `unreal_harness_runtime/python_exec.py`
- `unreal_harness_runtime/commandlet_exec.py`
- `unreal_orchestrator/server.py`
- `unreal_orchestrator/catalog.py`
- `pyproject.toml`

### 3. 高层命令优先
如果任务已经是高频、重复、易错工作流，优先做高层命令，不要继续堆裸属性写入。

### 4. 不要把 `material` 和 `material_graph` 混在一起
- `material`: 资产、实例、参数
- `material_graph`: 节点、连线、图重构

## 测试与交付
每个新功能至少做：

1. 一条成功路径
2. 一条错误路径
3. 一次重复执行
4. 一次失败后恢复检查

尽量补这些结果字段：

- `post_state`
- `verification.checks`
- batch 的 `summary + items`

## 静默工作流
静默启动 / 自动拉起编辑器只用于：

- MCP 功能开发
- MCP 回归测试
- 自动化验证

如果只是普通使用时出错，不要默认自动启动或重启编辑器。
这时应优先：

- 返回失败结果
- 返回当前 ready 状态
- 返回 `recommended_action`

只有在 MCP 开发/回归测试里，才允许显式调用 dev-only 工具：

- `dev_launch_editor_and_wait_ready`

如果需要自动循环测试：

1. 先看 `docs/workflow.md`
2. 需要活编辑器时静默启动 `UnrealEditor.exe`
3. 需要隔离导入时用 `UnrealEditor-Cmd.exe` commandlet
4. 启动后先做 smoke test，再做功能测试

## 完成前自检
- 是否只改了对应域的文件
- 是否说明是否需要重启编辑器/重编插件
- 是否记录已知限制
- 是否完成至少一条真实环境回归
- 是否说明当前结果校验状态
