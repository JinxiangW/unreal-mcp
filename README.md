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
- `unreal_scene/`, `unreal_asset/`, `unreal_material/`
  - 新子域 harness 的第一阶段骨架
  - 当前通过 `unreal_editor_mcp` 做 fallback 执行
- `RenderingMCP/`
  - Unreal 测试工程
  - `Plugins/UnrealMCP` 插件源码
- `config/mcp_config.example.json`
  - MCP 配置示例

## Python 依赖

```bash
pip install -r requirements.txt
```

## 启动 MCP

```bash
python -m unreal_editor_mcp.server
```

## 启动总控骨架

```bash
python -m unreal_orchestrator.server
```

默认连接到：

- `UE_HOST=127.0.0.1`
- `UE_PORT=55557`

可通过环境变量覆盖。

## Unreal 侧

使用 `RenderingMCP/RenderingMCP.uproject` 打开工程，确保 `Plugins/UnrealMCP` 被编译并启用。

## 当前暴露的主要工作流

- 资产浏览与属性读写
- Actor 创建、删除、批量修改
- 关卡与视口操作
- 纹理 / FBX 导入
- 材质图构建与分析
- Niagara 图与 Emitter 读写
- Blueprint 信息读取与高级图命令透传

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
- 测试方案：`docs/test-plan.md`
- 结果校验：`docs/verification.md`
- 静默工作流：`docs/workflow.md`

## 当前阶段

- `unreal_orchestrator` 已建立总控入口和分类目录
- `unreal_scene` / `unreal_asset` / `unreal_material` 已建立第一阶段高层接口骨架
- `unreal_editor_mcp` 现在主要作为 internal / fallback 层保留
- 下一阶段会把 `scene / asset / material asset` 逐步切到 UE Python 后端

## 提交约定

- 本仓库的提交信息统一使用中文。
