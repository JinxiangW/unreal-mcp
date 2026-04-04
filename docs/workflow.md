# 静默启动工作流

这份文档定义允许的静默启动与自动化测试工作流。

目标：

- 允许在不手工操作编辑器 UI 的前提下完成编译、启动、等待、测试、恢复
- 区分“需要活编辑器实例”的测试和“适合 commandlet 独立进程”的测试

## 适用边界

这份静默启动工作流只用于：

- MCP / harness 功能开发
- MCP / harness 回归测试
- 自动化验证

不用于普通使用场景的默认行为。

如果只是普通使用时遇到：

- 编辑器未打开
- 编辑器未 ready
- MCP 端口未恢复

默认做法应是：

- 返回当前状态
- 返回失败信息
- 返回 `recommended_action`

而不是自动帮用户静默启动或重启编辑器。

如果确实需要自动拉起编辑器，只允许通过显式的 dev-only 工具触发，而不是普通功能调用里隐式发生。

## 适用场景

### 需要活编辑器实例

- `scene` 高层命令
- `run_python` 相关流程
- 依赖当前打开关卡的操作
- 视口 / 相机 / 场景 Actor 编辑

### 适合独立 commandlet 进程

- `asset import`
- 大批量无 UI 资产导入
- 不依赖当前打开关卡和编辑器选择状态的任务

## 标准静默启动流程

### 1. 关闭旧编辑器实例

- 先确认没有旧的 `UnrealEditor.exe` 遗留
- 如果需要，强制关闭后再继续

### 2. 编译

- 如果改了 C++ / 插件：先编译再启动
- 如果只改 Python / 文档：不需要重编

### 3. 静默启动编辑器

推荐参数：

```powershell
Start-Process -FilePath $env:UE_EDITOR_EXE -ArgumentList @(
  $env:UE_PROJECT_PATH,
  "-NoSplash",
  "-NoSound",
  "-NoRHIValidation",
  "-SkipCompile"
) -WindowStyle Minimized
```

### 4. 等待 MCP 端口恢复

- 不要假设编辑器一启动就能测
- 必须轮询 `127.0.0.1:55557`

### 5. 预热检查

- `get_current_level`
- 如果使用 UE Python，还要确认 Python 已初始化

## 默认调用顺序

如果用户没有指定具体入口，默认按这个顺序：

1. `unreal_orchestrator`
2. `get_editor_ready_state`
3. 必要时 `wait_for_editor_ready`
4. 再执行 guarded 的域命令
5. 需要进一步缩 schema 时，优先切到 domain harness
6. `unreal_editor_mcp` raw 工具仅作为 internal / fallback

注意：

- 这套默认顺序不应隐式触发自动启动编辑器
- 自动启动只允许在 MCP 功能开发/回归测试里显式调用 dev-only 工具

## 静默工作流 Checklist

- 是否需要重编 C++ / 插件
- 是否已经关闭旧编辑器实例
- 是否等待端口恢复
- 是否做了最小 smoke test
- 是否记录了本轮是 live editor 还是 commandlet 流程

## 编辑器内执行 vs Commandlet 执行

### 编辑器内执行

适合：

- 需要当前场景上下文
- 需要当前 world / actor / viewport

风险：

- 会受当前编辑器状态影响
- 容易被用户手动操作打断

### Commandlet 执行

适合：

- 导入
- 大批量资产处理
- 无需当前场景上下文的流程

优势：

- 和活编辑器实例隔离
- 失败不会直接打掉当前场景编辑链

## 当前建议

- `scene`：优先 live editor 静默启动流程
- `asset import`：优先 commandlet
- `material parameter`：优先 live editor
- `material graph`：后续视实际执行模型决定

## Orchestrator 自动 preflight

当前 `unreal_orchestrator` 已开始对高风险的 live editor 命令自动做 preflight：

- 先检查 transport 是否可用
- 再检查 Unreal Python 是否 ready
- 再决定是否继续执行

因此后续更推荐通过 orchestrator 发高风险命令，而不是会话侧自己盲打 raw 工具。

## 当前恢复结果

当前仓库已经在真实 `MyToon` 项目上验证过下面链路：

- 强制关闭 `UnrealEditor`
- 重新静默启动
- 等待 transport 与 Unreal Python ready
- 再执行 orchestrator 查询命令完成 smoke test

这条恢复链路当前可用于 MCP / harness 开发与回归测试。

## 重试策略

不是所有命令都应该无限自动重试。

### 只读命令

- 最多重试 `3` 次
- 每次重试前先做 ready check
- 建议间隔：`2s -> 5s -> 10s`

### 幂等写命令

- 最多重试 `2` 次
- 每次重试前做 ready check
- 执行后要做回读，避免已经成功但又重复执行

### 非幂等写命令

- 默认不要自动整条重试
- 优先返回失败回执和失败日志

### commandlet 导入

- 最多补重试 `1` 次
- 必须带 `exit_code` 和结果文件/输出摘要

## 失败回执

失败时至少应返回：

- `operation`
- `attempt`
- `max_attempts`
- `error_type`
- `error_message`
- `transport_ok`
- `python_ready`
- `recommended_action`
- `log_tail`

如果是 commandlet，还应包含：

- `exit_code`
- `stdout_tail`
- `stderr_tail`

## 恢复要求

静默工作流失败后，必须至少做一项恢复确认：

- MCP 端口仍可连接
- 或 commandlet 退出码明确且主编辑器未受影响
- 或重启编辑器后 smoke test 恢复正常
