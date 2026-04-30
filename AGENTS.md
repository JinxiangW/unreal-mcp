# Agent 维护指南

默认使用中文回答，风格接近 CLI：直接、务实、少铺垫。处理任务时先给结论或下一步动作，再补充必要说明。

## 仓库定位

- 这是独立 Unreal Editor MCP 仓库。
- 默认对外入口是 `unreal_orchestrator`。
- `unreal_backend_tcp` 是内部 TCP backend，只负责 raw command、连接 Unreal 插件、result handle 和大结果处理。
- `RenderingMCP/Plugins/UnrealMCP` 是 UE 侧 C++ 插件。
- 不要把内部 raw backend 当成默认业务入口；只有高层工具缺能力或调试时才使用。

## 接手前阅读顺序

1. `skills/ue-harness/SKILL.md`
2. `docs/inventory.md`
3. `docs/categories.md`
4. 当前任务对应 domain 的 Python/C++ 文件
5. 必要时读 `docs/commands.md`
6. 必要时读 `docs/verification.md`
7. 必要时读 `docs/mcp-tool-gap-workflow.md`

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

- 优先使用 `unreal_orchestrator` 暴露的高层工具。
- orchestrator 不覆盖时，再进入 domain harness。
- `unreal_backend_tcp` raw command 和 `run_python` 只能作为 fallback。
- 如果同类 fallback 重复出现，按 `docs/mcp-tool-gap-workflow.md` 判断是否登记到 `docs/mcp-tool-gap-checklist.md`。
- 高风险 live-editor 操作前先确认 editor ready，必要时调用 `wait_for_editor_ready`。
- 普通工具调用不要隐式启动或重启编辑器；自动启动只用于显式 dev/debug 流程。

## 引擎源码定位

读 UE 源码前先解析当前项目对应引擎：

```powershell
python scripts\resolve_unreal_engine.py
```

- 优先使用输出里的 `engine_root` 和 `engine_source`。
- 不要把生成的 `.sln` 路径当作主依据，它可能已经过期。
- 查找顺序：项目 `Source/` 和 `Plugins/`，本仓库 UE 插件源码，解析出的 Engine `Source/`，Engine `Plugins/`，Engine `Content/Functions/`。
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

## C++ 插件改动规则

- 改 `RenderingMCP/Plugins/UnrealMCP` 后必须构建 `RenderingMCPEditor`。
- 推荐命令：

```powershell
& '<EngineRoot>\Build\BatchFiles\Build.bat' RenderingMCPEditor Win64 Development -Project='D:\ue-mcp\unreal-mcp\RenderingMCP\RenderingMCP.uproject' -WaitMutex -NoHotReload
```

- C++ 插件 DLL 改动后，已打开的 Unreal Editor 通常需要重启才能加载新逻辑。
- 最终说明里必须写清是否需要重启编辑器。

## 测试与验证

- Python 工具改动：跑 `python -m pytest -q`。
- Python 包/入口改动：跑 `python -m compileall <touched packages>`。
- UE 插件 C++ 改动：跑 UE `Build.bat`。
- 材质图/蓝图/资产关键路径能做 live UE 回归时，要记录真实资产或关卡路径。
- 如果不能做 live 回归，直接说明原因，不要声称已真实验证。
- `git diff --check` 用于提交前检查补丁格式。

## Git 规则

- 提交信息使用中文。
- 不要提交 `.vs/`、`.sln`、zip、外部 repo、IDE 生成文件、临时目录。
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
