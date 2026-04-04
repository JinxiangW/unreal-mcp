# 修复与清理 Checklist

状态：`[ ]` 未开始，`[-]` 进行中，`[x]` 已完成，`[!]` 阻塞。

## 基线

- [x] 确认 `5.6.1` 下 `RenderingMCPEditor / UnrealMCP` 可编译。
- [x] 确认 `127.0.0.1:55557` 可监听并可执行最小 MCP 命令。
- [x] 盘点当前工作树，区分“保留的修复”与“准备清理的内容”。

## 5.7 残留

- [x] 从仓库中彻底移除 `LookDevFull.umap / LookDevGray.umap / NewMaterial.uasset`。
- [x] 删除临时隔离目录 `_legacy_5_7_content/`。
- [x] 确认 `.uproject` 维持 `EngineAssociation = 5.6`。
- [x] 移除 `UnrealMCP.Build.cs` 中的 5.7 硬编码引擎路径。
- [x] 复扫源码、配置和文档，确认不再残留 5.7 资产路径或硬编码工程引用。

## 不需要内容

- [x] 删除误引入的 `RenderingMCP/Content/StarterContent/`。
- [x] 关闭 `DefaultGame.ini` 中的 `StarterContent` 自动注入。
- [x] 清理指向已删 `StarterContent` 的生成痕迹。
- [x] 复扫配置和文档，确认不再有 `StarterContent` 依赖。

## 传输层

- [x] 修复插件端 TCP 拆包，按累计字节解析完整 JSON。
- [x] 保持现有 `{type, params}` 客户端协议不变。
- [x] 补齐 Niagara bridge 分发表，消除已注册工具的 `Unknown command`。
- [x] 清理不再需要的旧收包实现与调试噪音。

## Scene / Orchestrator

- [x] 统一 actor 标识查找，支持 `actor label / object name` 双查找。
- [x] 修复 `set_scene_light_intensity` 的结构化返回与输入错误收口。
- [x] 修复 `create_spot_light_ring` 的查找逻辑与输入错误收口。
- [x] 修复 `spawn_actor_with_defaults` 的 target 标识混用。
- [x] 为 `query_scene_actors / query_scene_lights` 补 `actor_name / actor_label`。
- [x] 让 orchestrator guard 兜底 `ValueError`，避免输入错误直接冒泡成工具异常。

## 配置

- [x] 禁用 `RenderDocPlugin` 自动介入。
- [x] 保留当前可工作的 editor 启动链路配置。
- [x] 复核当前启动兜底，当前保留为稳定性修复，不继续扩散临时补丁。

## 验证

- [x] 重新编译 `RenderingMCPEditor`。
- [x] 回归 `ping / get_current_level / TCP 拆包`。
- [x] 回归 scene 域的 label 查找与结构化输入错误。
- [x] 回归 orchestrator 对输入错误的结构化失败。

## 收尾

- [x] 更新 checklist 为最终状态。
- [x] 检查工作树，只保留需要提交的修复与清理。
- [x] 提交一个包含本轮修复与清理的 commit。
