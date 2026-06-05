# Agent 维护指南

默认使用中文回答，风格接近 CLI：直接、务实、少铺垫。处理任务时先给结论或下一步动作，再补充必要说明。

## 仓库定位

- 这是独立 Unreal Editor MCP 仓库。
- 域业务入口是各 `unreal_<domain>/server.py`（独立 FastMCP server）。
- `unreal_orchestrator` 仅暴露 3 个路由/发现工具，不再聚合域业务工具。
- `unreal_backend_tcp` 是内部 TCP backend，只负责 raw command、连接 Unreal 插件、result handle 和大结果处理。
- 本仓库不包含 UE 测试工程；UE 侧插件按目标项目侧配置维护。
- 不要把内部 raw backend 当成默认业务入口；只有高层工具缺能力或调试时才使用。

## 接手前阅读顺序

1. `docs/agent-quickstart.md`（默认入口、domain 选择、token 禁忌）
2. `.claude/skills/ue-harness/SKILL.md`（完整规则）
3. 当前任务对应 domain 的 Python 文件
4. 必要时读 `.claude/skills/ue-harness/` 下的对应参考文件

## 域边界

- `scene`：关卡、Actor、灯光、后处理、viewport、组件级场景操作。
- `asset`：通用资产 CRUD、导入、批处理、资产属性读写、贴图/Cascade 资产检查。
- `material`：Material / MaterialInstance / MaterialFunction 资产和参数工作流。
- `material_graph`：材质图读取、分析、节点创建、连接、patch、属性连接。
- `blueprint`：蓝图结构读取、图节点发现、节点创建、pin/default 设置、连线。
- `diagnostics`：ready state、transport、runtime policy、token/进程/commandlet 诊断。
- `renderdoc`：UE 侧 RenderDoc 捕获控制、上下文 sidecar、选择对象映射、符号反查。

不要把 `material` 和 `material_graph` 混在一起：材质资产/实例/参数属于 `material`，节点图编辑属于 `material_graph`。

## 默认调用策略

- 域业务工具优先连接对应域 server（`python -m unreal_<domain>.server`）。
- `unreal_orchestrator` 仅用于路由/发现（`get_harness_domains` / `get_domain_design` / `route_harness_task`）。
- `unreal_backend_tcp` raw command 和 `run_python` 只能作为 fallback。
- 如果同类 fallback 重复出现，按 `.claude/skills/ue-harness/mcp-tool-gap-workflow.md` 判断是否登记到 `mcp-tool-gap-checklist.md`。
- 高风险 live-editor 操作前先确认 editor ready，必要时调用 `wait_for_editor_ready`。
- 普通工具调用不要隐式启动或重启编辑器；自动启动只用于显式 dev/debug 流程。

## 引擎源码定位

读 UE 源码前先解析当前项目对应引擎：

```powershell
python .claude\skills\ue-harness\scripts\resolve_unreal_engine.py
```

- 优先使用输出里的 `engine_root` 和 `engine_source`。
- 不要把生成的 `.sln` 路径当作主依据，它可能已经过期。
- 查找顺序：项目 `Source/` 和 `Plugins/`，解析出的 Engine `Source/`，Engine `Plugins/`，Engine `Content/Functions/`。
- 回答或提交说明里如果依赖了 UE 源码判断，要写明使用的 engine 路径或说明源码不可用。

## 材质图维护规则

- 图编辑后必须 readback，不能只信 `success: true`。
- 检查关键 `nodes`、`connections`、`property_connections`。
- 高风险分支要逐段构建、逐段验证。
- 修改或重建 `MaterialFunction` 后，要刷新父材质或相关 `MaterialFunctionCall`。
- 优先使用原生 UE material node；官方/项目材质函数用 `MaterialFunctionCall`。
- `Custom` 只用于确实缺原生节点或源材料本来就是自定义逻辑的场景。
- 不要新增或修 `Custom.include_file_paths` 方向，避免引入 shader virtual path 和 shader mapping 依赖。

## 资产与批处理规则

- 批量工具返回结构要包含 `summary`、`items`、`post_state`、`verification`。
- enum 返回和校验要归一化，优先返回 `{ "name": "...", "value": ... }`。
- 大批量操作要内置 chunking 或明确限制，避免 orchestrator 超时。
- 写属性后要统一执行：改属性、标脏、保存、必要时重建资源、回读验证。
- 查询类工具要在枚举阶段做 class 过滤，不要等读属性失败后再过滤。

## 测试与验证

- Python 工具改动：跑 `python -m pytest -q`。
- Python 包/入口改动：跑 `python -m compileall <touched packages>`。
- 材质图/蓝图/资产关键路径能做 live UE 回归时，要记录真实资产或关卡路径。
- 如果不能做 live 回归，直接说明原因，不要声称已真实验证。
- `git diff --check` 用于提交前检查补丁格式。

## Git 规则

- 提交信息使用中文，格式：`<类型>: <简短描述>`。
  - 类型：`feat` 新功能 / `fix` 修复 / `refactor` 重构 / `docs` 文档 / `test` 测试 / `chore` 杂项
  - 示例：`重构MCP工具架构，拆分为独立域服务器`
- 一个 commit 只做一件事，避免混合无关改动。
- 不要提交 `.vs/`、`.sln`、zip、外部 repo、IDE 生成文件、临时目录、`.egg-info/`。
- 不要回滚用户未授权改动。
- 工作区有无关脏文件时，只 stage 本次任务相关文件。
- 推送前确认：

```powershell
git status --short --branch
git log --oneline origin/master..master
```

## 交付说明

完成后简短说明：

- 改了什么。
- 为什么这样改。
- 验证跑了什么。
- 是否需要重启编辑器或 MCP。
- 哪些已有脏文件被保留未处理。
