# Harness 分类索引

这份文档不是功能说明，而是给后续 AI / harness 工程师做“最小阅读路由”的索引。

目标：

- 遇到某类任务时，只看对应文件
- 遇到某类故障时，先查对应层级
- 避免每次都把整个仓库重新读一遍

## 分类原则

本仓库按两条轴来理解：

1. 分层：请求是怎么从 MCP 到 UE 执行的
2. 分域：命令实际在操作什么对象

建议先按“分域”定位，再按“分层”排障。

## 分层

### 1. Python MCP 层

职责：

- 暴露 FastMCP server
- 定义对外工具面
- 负责 TCP 请求发送与基础错误包装

关键文件：

- `unreal_editor_mcp/server.py`
- `unreal_editor_mcp/tools.py`
- `unreal_editor_mcp/connection.py`
- `unreal_editor_mcp/common.py`

什么时候看这层：

- OpenCode / MCP 无法启动
- 工具名、参数名、Python 包导入有问题
- 想确认对外暴露了哪些工作流

### 2. 传输层

职责：

- UE 插件监听 TCP
- 收包、发包、连接生命周期

关键文件：

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/MCPServerRunnable.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/MCPServerRunnable.h`

什么时候看这层：

- `Connection closed`
- `Client disconnected`
- UE 端口不监听
- 收到请求但没有回包

### 3. 桥接分发层

职责：

- 把命令名路由到具体命令处理器
- 定义“插件真实支持哪些命令”

关键文件：

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/EpicUnrealMCPBridge.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/EpicUnrealMCPBridge.h`

什么时候看这层：

- `Unknown command`
- Python 暴露了工具，但 UE 返回不支持
- 想确认某个命令到底被注册到哪个命令组

### 4. 共享写入 / 反射工具层

职责：

- 通用属性读写
- enum / struct / color / 组件属性映射的底层支撑
- JSON <-> UObject/FProperty 转换

关键文件：

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPCommonUtils.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPCommonUtils.h`

什么时候看这层：

- `Property not found`
- `Unsupported property type`
- struct 写不进去
- enum / 颜色 / 名字大小写写入异常

### 5. 领域命令层

职责：

- 面向对象域做真实业务操作
- 例如场景 Actor、材质图、Niagara、蓝图图

关键文件见“分域”章节。

## 分域

### A. 场景与环境编辑

覆盖内容：

- `spawn_actor`
- `delete_actor`
- `get_actors`
- `set_actor_properties`
- `batch_set_actors_properties`
- 关卡与视口相关命令
- 灯光、后处理、Actor transform、组件属性路由

关键文件：

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPEnvironmentCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPEnvironmentCommands.h`
- 关联共享层：
  - `EpicUnrealMCPCommonUtils.cpp`
  - `EpicUnrealMCPBridge.cpp`

AI 遇到这些任务时只看：

- 场景布光
- 后处理体积编辑
- 批量 Actor 摆放
- 视口截图 / 相机控制
- 关卡创建 / 加载 / 保存

典型风险：

- Actor 属性不一定在 Actor 本体，而在组件上
- 灯光单位和强度不能只写 `Intensity`
- `SpotLight` 默认 `Stationary`，容易触发重叠告警
- `PostProcessVolume.Settings` 是 struct，不是普通字段

### B. 资产与通用编辑器操作

覆盖内容：

- 通用资产创建/删除
- 资产属性读写
- 批量资产创建/更新
- 纹理 / FBX 导入

关键文件：

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPEditorCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPEditorCommands.h`

AI 遇到这些任务时只看：

- 创建材质实例之外的通用资产
- 改资产属性
- 导入资源文件

### C. 材质与贴图工作流

覆盖内容：

- 创建材质 / 材质函数 / 材质实例
- 构建材质图
- 读取材质图
- 设置材质实例参数
- 导入纹理

关键文件：

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPMaterialCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPMaterialCommands.h`

AI 遇到这些任务时只看：

- 创建 `DefaultLit` 材质
- 连节点
- 创建 MI 并设置参数

### D. Niagara 工作流

覆盖内容：

- 读取 Niagara graph
- 更新 Niagara graph
- 读取 emitter
- 更新 emitter

关键文件：

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPNiagaraCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPNiagaraCommands.h`

AI 遇到这些任务时只看：

- Niagara system/emitter 检查
- Niagara 图操作

### E. 蓝图高层信息与编辑

覆盖内容：

- 读取 blueprint 内容
- 分析 graph
- Editor Utility Widget 相关 info/update

关键文件：

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPBlueprintCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPBlueprintCommands.h`

AI 遇到这些任务时只看：

- 读取 blueprint 元信息
- 做 blueprint 内容分析
- 非 graph 级的蓝图更新

### F. 蓝图图编辑

覆盖内容：

- 加节点
- 连线
- 创建变量
- 设置变量属性
- 创建函数与输入输出
- 删除节点 / 函数

关键文件：

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPBlueprintGraphCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPBlueprintGraphCommands.h`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/BlueprintGraph/**/*.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/BlueprintGraph/**/*.h`

AI 遇到这些任务时只看：

- blueprint graph 结构改动
- 自定义节点管理
- 函数 / 变量 / 事件节点操作

说明：

- 这是最重的一组文件
- 如果不是 graph 级编辑，不要先读这组

## 按任务路由：AI 最小阅读集合

### 任务：MCP 连不上 / 本地 server 启不来

先读：

- `unreal_editor_mcp/server.py`
- `unreal_editor_mcp/connection.py`
- `MCPServerRunnable.cpp`

### 任务：工具有，但 UE 返回 `Unknown command`

先读：

- `unreal_editor_mcp/tools.py`
- `EpicUnrealMCPBridge.cpp`

### 任务：场景灯光 / 后处理 / Actor 编辑失败

先读：

- `EpicUnrealMCPEnvironmentCommands.cpp`
- `EpicUnrealMCPCommonUtils.cpp`
- `EpicUnrealMCPBridge.cpp`

### 任务：材质创建 / 连线有问题

先读：

- `EpicUnrealMCPMaterialCommands.cpp`
- `unreal_editor_mcp/tools.py`

### 任务：Niagara 操作有问题

先读：

- `EpicUnrealMCPNiagaraCommands.cpp`
- `unreal_editor_mcp/tools.py`

### 任务：蓝图信息读取/更新异常

先读：

- `EpicUnrealMCPBlueprintCommands.cpp`
- `unreal_editor_mcp/tools.py`

### 任务：蓝图 graph 操作异常

先读：

- `EpicUnrealMCPBlueprintGraphCommands.cpp`
- `Commands/BlueprintGraph/**/*.cpp`

## 按故障路由：AI 最小阅读集合

### 症状：`Unknown command`

优先看：

- `EpicUnrealMCPBridge.cpp`

常见根因：

- Python 侧已暴露，bridge 未注册

### 症状：`Property not found`

优先看：

- `EpicUnrealMCPEnvironmentCommands.cpp`
- `EpicUnrealMCPCommonUtils.cpp`

常见根因：

- 属性在组件上，不在 Actor 上
- 大小写 / 命名风格不一致
- 需要专用 setter，而不是普通属性写入

### 症状：`Unsupported property type: StructProperty`

优先看：

- `EpicUnrealMCPCommonUtils.cpp`

常见根因：

- 缺少 struct 递归写入
- 后处理 `Settings` 这类大 struct 未做特判

### 症状：`Connection closed` / 没有回包

优先看：

- `MCPServerRunnable.cpp`
- `EpicUnrealMCPBridge.cpp`
- 当前运行实例对应的 UE 日志

常见根因：

- 请求执行过程中未正确构造响应
- 当前日志不是当前运行实例的日志

## 当前已知高风险区

这些场景请优先把 AI 路由到“场景与环境编辑”分类，不要只靠通用属性写入推断：

- 灯光强度单位
- `SpotLight` 朝向
- `Mobility`
- `LightColor`
- `PostProcessVolume.Settings`
- 批量 Actor transform + properties 混合写入

## 维护建议

后续如果新增命令，至少同步更新两处：

1. `unreal_editor_mcp/tools.py`
2. `docs/categories.md`

如果是 UE 侧新增命令，还要同步确认：

3. `EpicUnrealMCPBridge.cpp`

这份文档的目标不是“完整”，而是保证 AI 在大多数任务里能先读最少的正确文件。
