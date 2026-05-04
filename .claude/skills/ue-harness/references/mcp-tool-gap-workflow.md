# MCP 工具缺口检测流程（Tool Gap Workflow）

> **Language convention**: detection steps, priority scale, and output rules are in English. Goal descriptions and lifecycle explanations are in Chinese.

## 目标

在保证正常任务推进的同时，将可复现的 MCP 能力缺口集中记录，用于后续实现。

Agent 不应每次遇到 fallback 就停下来。应在安全完成用户任务后，将有足够证据的缺失或薄弱 MCP 能力记录下来。

## 什么算缺口

满足以下任一条件时记录缺口：

- 针对用户意图的高层 MCP 工具不存在
- 高层 MCP 工具存在但缺少任务所需字段
- 高层 MCP 工具返回混乱、模糊或未规范化的数据，强制额外过滤
- 高层 MCP 工具报告失败但 UE 操作实际已成功，或报告成功但缺乏足够验证
- Agent 必须使用 `run_python`、raw backend 命令、本地 Python 导入或编辑器反射来完成正常的用户工作流
- 同一个 Python workaround 或手动检查可能被复用于其他资产、图、蓝图、场景或渲染调试任务
- MCP 操作仅对小规模用例有效，但无法处理正常批处理大小、超时、保存、编译或事务需求

以下情况不记录：

- 一次性源码阅读、grep、构建、测试或本地文件检查
- 用户明确要求执行任意 Python
- 任务为探索性，尚无明确的稳定用户工作流
- MCP 工具已支持该工作流，Agent 仅因便利而使用 Python

## 检测步骤

1. Classify the domain: `scene / asset / material / material_graph / blueprint / niagara / diagnostics / renderdoc`
2. Check the relevant domain server first, then `unreal_orchestrator` for routing/discovery if the domain is unclear
3. Check `inventory.md`, `commands.md`, and the domain tool module before falling back
4. If a fallback is used, identify whether it was for missing capability, missing fields, incorrect behavior, stability, performance, or poor error reporting
5. Complete the user task if the fallback is safe and verifiable
6. Append a new item to `mcp-tool-gap-checklist.md`

## 条目生命周期（Item Lifecycle）

- New repeatable gaps go under "待处理条目" (Open Items) with `Status: open`
- When implementation starts, change to `Status: in_progress` only if actively being worked on
- After implementation and verification, change to `Status: done`, add concise verification notes, and move to "已完成条目" (Done Items)
- Do not delete completed items — retained as implementation history and regression context
- 待处理条目中只应包含仍需解决的缺口

## 必要证据

每个检查清单条目必须包含：

- 域和受影响工具
- 失败或需要 fallback 的用户工作流
- 使用的具体 fallback，如 `run_python`、raw command、本地导入或手动源码阅读
- 预期的 MCP 行为
- 最小建议的工具或参数变更
- 实现后应通过的验证场景

## 优先级

使用以下优先级：

- `P0`：阻塞常见工作流或可能破坏资产/图
- `P1`：常见工作流需要 fallback 或返回错误的成功/失败
- `P2`：缺少字段、错误详情不足或 API 可用但别扭
- `P3`：便利封装或纯文档改进

## 输出规则

当仓库可写时，将条目追加到 `mcp-tool-gap-checklist.md`。

当仓库不可写时，在最终回复的 `MCP Tool Gap` 下包含相同的检查清单条目。

不要将实现细节与推测混在一起。如果根因未知，写"根因未知"并保持证据具体。

## 实现就绪条件

缺口在包含以下内容后即具备实现条件：

- 可复现的任务或资产路径模式
- 当前工具行为
- 成功或部分成功的 fallback
- 期望的稳定 MCP 契约
- 至少一个验收测试或真实回归目标
