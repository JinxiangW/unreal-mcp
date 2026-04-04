# unreal-mcp

从 `TAAgent` 抽离出来的独立 Unreal Editor MCP。

## 包含内容

- `unreal_editor_mcp/`
  - 独立 Python MCP server
  - TCP 连接 Unreal 插件
  - 当前主要作为 internal / fallback 层保留
- `unreal_orchestrator/`
  - 新的总控 harness 骨架
  - 负责问题域路由与能力目录
- `unreal_scene/`, `unreal_asset/`, `unreal_material/`, `unreal_material_graph/`
  - 新子域 harness 的第一阶段骨架
  - 当前通过 `unreal_editor_mcp` 或 wrapper backend 做 fallback 执行
- `RenderingMCP/`
  - Unreal 测试工程
  - `Plugins/UnrealMCP` 插件源码
- `config/mcp_config.example.json`
  - MCP 配置示例

## Python 依赖

```bash
pip install -r requirements.txt
```

## 启动默认 MCP

```bash
python -m unreal_orchestrator.server
```

## 启动 raw / internal MCP

```bash
python -m unreal_editor_mcp.server_internal
```

## 启动 domain harness

```bash
python -m unreal_scene.server
python -m unreal_asset.server
python -m unreal_material.server
python -m unreal_material_graph.server
```

默认连接到：

- `UE_HOST=127.0.0.1`
- `UE_PORT=55557`
- `UE_PROJECT_PATH=<当前工作 .uproject>`
- `UE_EDITOR_EXE=<UnrealEditor.exe 路径>`
- `UE_EDITOR_CMD=<UnrealEditor-Cmd.exe 路径>`

可通过环境变量覆盖。

## Unreal 侧

使用 `RenderingMCP/RenderingMCP.uproject` 打开工程，确保 `Plugins/UnrealMCP` 被编译并启用。

## 当前默认架构

- `unreal_orchestrator`
  - 默认入口
  - 默认只暴露高层命令、诊断能力和 compact 查询
- `unreal_scene` / `unreal_asset` / `unreal_material`
  - domain harness
  - 适合按域加载，进一步减少默认 schema
- `unreal_material_graph`
  - 已进入最小可用阶段
  - 当前负责材质图读取、分析和 recipe 构建包装
- `unreal_editor_mcp`
  - internal / debug / fallback
  - 保留完整 raw 工具面

## 当前暴露的主要工作流

- 资产浏览与属性读写
- Actor 创建、删除、批量修改
- 关卡与视口操作
- 纹理 / FBX 导入
- 材质图构建与分析
- Niagara 图与 Emitter 读写
- Blueprint 信息读取与高级图命令透传
- 高层摘要查询：`query_scene_actors`、`query_scene_lights`、`query_assets_summary`
- 高层写入工作流：`ensure_asset_with_properties`、`update_material_instance_parameters_and_verify`
- 资产收尾命令：`ensure_folder`、`duplicate_asset_with_overrides`、`move_asset_batch`
- 材质图域命令：`analyze_material_graph`、`create_material_graph_recipe`、`connect_material_nodes`

## Harness 索引

- Repo skill：`skills/ue-harness/SKILL.md`
- Unity->UE 迁移 skill：`skills/unity-to-ue/SKILL.md`
- Unity->UE 迁移案例：`docs/migrations/README.md`
- legacy 定位与退役清单：`docs/legacy.md`
- 分类索引：`docs/categories.md`
- 架构方案：`docs/proposal.md`
- 架构图：`docs/architecture.html`
- 功能清单：`docs/inventory.md`
- 高层命令：`docs/commands.md`
- 并行 checklist：`docs/parallel.md`
- token 优化 checklist：`docs/token-optimization-checklist.md`
- 测试方案：`docs/test-plan.md`
- 结果校验：`docs/verification.md`
- 静默工作流：`docs/workflow.md`

## 当前阶段

- `unreal_orchestrator` 已作为默认入口，默认工具集已压缩
- `unreal_scene` / `unreal_asset` / `unreal_material` 已可作为独立 domain harness 启动
- `unreal_editor_mcp` 现在主要作为 internal / fallback 层保留
- 查询、图类、批量、属性类工具已接入摘要返回策略
- 大结果已支持 `saved_to` / `result_handle`，并支持超阈值自动 offload

## 提交约定

- 本仓库的提交信息统一使用中文。
