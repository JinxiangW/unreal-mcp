# unreal-mcp

从 `TAAgent` 抽离出来的独立 Unreal Editor MCP。

## 目录

- `unreal_mcp/`
  - 统一对外入口，聚合所有域工具（~80 tools）
- `unreal_orchestrator/`
  - 路由与发现入口（3 个工具，可选）
- `unreal_backend_tcp/`
  - 内部 TCP backend，负责连接 Unreal 插件、raw command、result handle
- `unreal_scene/` — scene 域高层命令
- `unreal_asset/` — asset 域高层命令、导入、批处理
- `unreal_blueprint/` — blueprint 域
- `unreal_material/` — material asset / instance / parameter 工作流
- `unreal_material_graph/` — material graph 读取、分析、recipe 构建
- `unreal_renderdoc/` — UE 侧 RenderDoc 捕获控制与上下文收集
- `unreal_diagnostics/` — health、ready、transport、token 诊断
- `RenderingMCP/` — Unreal 测试工程与 `Plugins/UnrealMCP`

## 启动

默认入口：

```bash
python -m unreal_mcp.server
```

单独域或 orchestrator（按需）：

```bash
python -m unreal_orchestrator.server  # 仅路由/发现
python -m unreal_scene.server         # 仅场景工具
python -m unreal_asset.server         # 仅资产工具
```

## 环境变量

- `UE_HOST=127.0.0.1`
- `UE_PORT=55557`
- `UE_PROJECT_PATH=<.uproject>`
- `UE_ENGINE_ROOT=<Engine directory, optional>`
- `UE_EDITOR_EXE=<UnrealEditor.exe>`
- `UE_EDITOR_CMD=<UnrealEditor-Cmd.exe>`

## MCP 客户端配置

- 默认配置：`config/mcp_config.example.json`
  - 使用 `python -m unreal_mcp.server`
  - 直接暴露 `scene`、`asset`、`material`、`material_graph`、`diagnostics`、`renderdoc` 等高层工具
- `unreal_orchestrator.server` 只用于可选路由/发现，不作为默认工具面
- RenderDoc sidecar 配置见 `config/mcp_config.multi-server.example.json`

解析当前项目对应引擎源码路径：

```bash
python .claude/skills/ue-harness/scripts/resolve_unreal_engine.py
```

## 当前结构

- 统一对外入口：`unreal_mcp/server.py`（聚合所有域工具，~80 tools）
- 内部 backend：`unreal_backend_tcp`
- 各域 `server.py` 可独立运行（仅按需调试时使用）
- `unreal_orchestrator` 仅提供路由/发现（3 个工具，可选）
- MCP 客户端配置见 `config/mcp_config.example.json`

## 文档

- `docs/architecture.html`
- `.claude/skills/ue-harness/` — skill 主入口及全部参考文档
## 提交约定

- 提交信息统一使用中文
