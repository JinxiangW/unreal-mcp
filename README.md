# unreal-mcp

从 `TAAgent` 抽离出来的独立 Unreal Editor MCP。

## 目录

- `unreal_orchestrator/`
  - 路由与发现入口（3 个工具：`get_harness_domains` / `get_domain_design` / `route_harness_task`）
  - 不承载域业务工具，域工具由各自 server 独立暴露
- `unreal_backend_tcp/`
  - 唯一内部 TCP backend
  - 负责连接 Unreal 插件、raw command、result handle
- `unreal_scene/`
  - scene 域高层命令与 compact 查询
- `unreal_asset/`
  - asset 域高层命令、导入、批处理
- `unreal_material/`
  - material asset / instance / parameter 工作流
- `unreal_material_graph/`
  - material graph 读取、分析、recipe 构建
- `unreal_diagnostics/`
  - health、ready、transport、token 诊断
- `RenderingMCP/`
  - Unreal 测试工程与 `Plugins/UnrealMCP`

## 启动

多服务器模式（推荐，各域独立）：

```bash
python -m unreal_scene.server       # 场景编辑
python -m unreal_asset.server       # 资产管理
python -m unreal_blueprint.server   # 蓝图编辑
python -m unreal_material.server    # 材质工作流
python -m unreal_material_graph.server  # 材质图编辑
python -m unreal_renderdoc.server   # RenderDoc 捕获
python -m unreal_diagnostics.server # 诊断
```

单入口模式（仅路由/发现，不含域工具）：

```bash
python -m unreal_orchestrator.server
```

## 环境变量

- `UE_HOST=127.0.0.1`
- `UE_PORT=55557`
- `UE_PROJECT_PATH=<.uproject>`
- `UE_ENGINE_ROOT=<Engine directory, optional>`
- `UE_EDITOR_EXE=<UnrealEditor.exe>`
- `UE_EDITOR_CMD=<UnrealEditor-Cmd.exe>`

解析当前项目对应引擎源码路径：

```bash
python scripts/resolve_unreal_engine.py
```

## 当前结构

- 路由/发现入口：`unreal_orchestrator`（仅 3 个路由工具）
- 域业务入口：各 `unreal_<domain>/server.py`（独立 FastMCP server，自带 editor guard）
- 内部 backend：`unreal_backend_tcp`
- scene / asset / material / blueprint / material_graph 优先走对应域 server
- 多服务器 MCP 配置见 `config/mcp_config.multi-server.example.json`

## 文档

- `docs/architecture.html`
- `.claude/skills/ue-harness/` — skill 主入口及全部参考文档
## 提交约定

- 提交信息统一使用中文
