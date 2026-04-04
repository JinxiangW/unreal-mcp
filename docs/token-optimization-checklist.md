# Token 优化 Checklist

状态：`[ ]` 未开始，`[-]` 进行中，`[x]` 已完成，`[!]` 阻塞。

## 基线

- [x] 记录 `schema / input / output / total` token 估算与 `latency`。
- [x] 输出高成本工具 Top 10。
- [x] 区分冷启动和热会话成本。

## 工具集

- [x] 常规模式只暴露 `unreal_orchestrator`。
- [x] `unreal_editor_mcp` 改成 internal / debug 入口。
- [x] dev-only 工具不进入默认 schema。
- [x] 按域动态加载 toolset。

## 返回体

- [x] `diagnostics` 默认走 compact 返回。
- [x] guarded 调用默认不展开完整 `preflight`。
- [x] 查询类工具统一支持 `summary_only`、`fields`、`limit`。
- [x] 批量工具默认只回 `summary + failed_items`。

## 大对象

- [x] `material graph / niagara / blueprint` 默认只回摘要。
- [x] 超阈值结果统一走 `result_handle` 或 `saved_to`。
- [x] HLSL、完整图、完整蓝图内容默认不内联。

## 高层命令

- [x] 用高层命令替代“查 -> 拼 -> 调 -> 回读”多轮链路。
- [x] 常见查询改成服务端筛选，不让模型自己筛全量结果。
- [x] 写操作优先提供“更新并验证”接口。

## 配置

- [x] 用 `UE_PROJECT_PATH` 统一当前工作项目。
- [x] 用 `UE_EDITOR_EXE` / `UE_EDITOR_CMD` 统一编辑器路径。
- [x] 配置读取统一走共享 runtime config。

## 验收

- [x] 冷启动 schema token 下降 `50%+`。
- [x] 常见查询 token 下降 `60%+`。
- [x] 图类默认调用 token 下降 `80%+`。
- [x] 平均工具调用次数下降 `30%+`。
- [x] 成功率下降不超过 `3%`。

## MyToon 回归

- [x] 切到 `D:\UnrealProjects\MyToon\MyToon.uproject`。
- [x] 完成静默启动 smoke test。
- [x] 完成 `ready state / current level` 回归。
- [x] 引擎异常退出后可自动重启并继续测试。
