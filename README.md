# unreal-mcp

从 `TAAgent` 抽离出来的独立 Unreal Editor MCP。

## 包含内容

- `unreal_editor_mcp/`
  - 独立 Python MCP server
  - TCP 连接 Unreal 插件
  - 资产 / Actor / Level / Viewport / Material / Niagara / Blueprint 工作流
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
