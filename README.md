# unreal-mcp

从 `TAAgent` 抽离出来的独立 Unreal Editor MCP。

## 目录

- `unreal_orchestrator/`
  - 默认对外入口
  - 负责域路由、ready preflight、结果包装
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

默认入口：

```bash
python -m unreal_orchestrator.server
```

按域启动：

```bash
python -m unreal_scene.server
python -m unreal_asset.server
python -m unreal_material.server
python -m unreal_material_graph.server
```

## 环境变量

- `UE_HOST=127.0.0.1`
- `UE_PORT=55557`
- `UE_PROJECT_PATH=<.uproject>`
- `UE_EDITOR_EXE=<UnrealEditor.exe>`
- `UE_EDITOR_CMD=<UnrealEditor-Cmd.exe>`

## 当前结构

- 默认业务入口：`unreal_orchestrator`
- 内部 backend：`unreal_backend_tcp`
- scene / asset / material 优先走高层 harness
- material graph 当前仍保留内部 raw backend 支撑，但不再通过 legacy 包名暴露

## 文档

- `docs/architecture.html`
- `docs/inventory.md`
- `docs/categories.md`
- `docs/commands.md`
- `docs/verification.md`
- `docs/test-plan.md`
- `docs/workflow.md`
- `docs/proposal.md`

## 提交约定

- 提交信息统一使用中文
