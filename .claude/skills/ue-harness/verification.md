# 结果获取与正确性校验机制

这份文档定义新 harness 必须具备的结果验证机制。

目标：

- 不只返回 `success: true`
- 明确知道“改了什么、哪些成功、哪些失败、最终状态是什么”
- 让后续自动化直接判断结果是否正确

## 核心原则

### 1. 执行成功不等于结果正确

写操作必须区分两层结果：

- 执行结果：命令是否成功执行
- 状态结果：目标对象最终是否达到预期

### 2. 必须有结构化回执

最少应包含：

- `success`
- `operation_id`
- `domain`
- `targets`
- `applied_changes`
- `failed_changes`
- `post_state`
- `verification`

### 3. 必须有回读校验

写操作完成后默认执行回读。

## 推荐返回结构

```json
{
  "success": true,
  "operation_id": "scene:create_spot_light_ring:2026-04-03T12:00:00Z:abcd1234",
  "domain": "scene",
  "targets": ["MCP_RingSpot_01", "MCP_RingSpot_02"],
  "applied_changes": [
    {"target": "MCP_RingSpot_01", "field": "intensity", "value": 9}
  ],
  "failed_changes": [],
  "post_state": {
    "MCP_RingSpot_01": {
      "intensity": 9,
      "intensity_units": "CANDELAS",
      "mobility": "MOVABLE"
    }
  },
  "verification": {
    "verified": true,
    "checks": [
      {"target": "MCP_RingSpot_01", "field": "intensity", "expected": 9, "actual": 9, "ok": true}
    ]
  }
}
```

## verification 字段要求

- `verified`: 总体验证是否通过
- `checks`: 每条断言结果

每条 check 最少包含：

- `target`
- `field`
- `expected`
- `actual`
- `ok`

## 大批量操作的结果模型

批处理不能只返回一个总成功/失败。

必须返回：

- 总数
- 成功数
- 失败数
- 每个对象的结果
- 每个对象的回读校验结果

推荐结构：

```json
{
  "success": false,
  "operation_id": "asset:batch_import:...",
  "summary": {
    "requested": 100,
    "succeeded": 97,
    "failed": 3,
    "verified": 95
  },
  "items": [
    {
      "target": "/Game/Foo/A",
      "success": true,
      "verification": {"verified": true, "checks": []}
    },
    {
      "target": "/Game/Foo/B",
      "success": false,
      "error": "Asset already exists"
    }
  ]
}
```

## 查询类命令的结果模型

查询类命令也必须返回统一结构，但 `summary` 的语义和写操作不同。

推荐最小字段：

- `requested`
- `returned`
- `total`
- `failed`
- `verified`
- `offset`

同时建议补：

- `filters`
- `items`

其中：

- `requested` 表示请求的 `limit`
- `returned` 表示本次实际返回条目数
- `total` 表示服务端可见总数
- `failed` 对查询类通常固定为 `0`
- `verified` 对查询类通常等于 `returned`
- `offset` 表示分页起点

推荐结构：

```json
{
  "success": true,
  "operation_id": "scene:query_scene_lights:...",
  "domain": "scene",
  "targets": ["KeyLight_A", "FillLight_B"],
  "applied_changes": [],
  "failed_changes": [],
  "post_state": {
    "scene_query": {
      "lights": []
    }
  },
  "verification": {
    "verified": true,
    "checks": []
  },
  "summary": {
    "requested": 20,
    "returned": 2,
    "total": 2,
    "failed": 0,
    "verified": 2,
    "offset": 0
  },
  "filters": {
    "limit": 20,
    "offset": 0
  },
  "items": [
    {
      "target": "KeyLight_A",
      "success": true,
      "verification": {
        "verified": true,
        "checks": []
      }
    }
  ]
}
```

## 失败回执模型

失败结果不应只返回一行错误字符串。

推荐最小结构：

```json
{
  "success": false,
  "operation": "scene.set_scene_light_intensity",
  "attempt": 2,
  "max_attempts": 3,
  "error_type": "timeout_error",
  "error_message": "Editor is not ready for this live-editor operation",
  "transport_ok": true,
  "python_ready": false,
  "recommended_action": "wait_and_retry",
  "log_tail": []
}
```

如果是 commandlet，还应补：

- `exit_code`
- `stdout_tail`
- `stderr_tail`
- `result_file` 或解析结果

## 批处理专项要求

所有支持批处理的域，后续都必须测试：

- 小批量：10
- 中批量：50
- 大批量：100 起步
- 部分失败：5% 到 20% 人为失败项

## 域内断言器建议

### Scene

- `assert_actor_transform`
- `assert_light_state`
- `assert_post_process_override`

### Asset

- `assert_asset_exists`
- `assert_asset_class`
- `assert_asset_property`
- `assert_import_count`

### Material

- `assert_material_instance_parameter`
- `assert_material_parameter_names`

### Material Graph

- `assert_material_node_exists`
- `assert_material_connection_exists`

## 当前阶段建议

先按这个顺序推进：

1. 新高层命令先加 `post_state`
2. 再加 `verification.checks`
3. 最后给 batch 命令统一 `summary + items`

## 通过标准

一个功能只有同时满足下面条件，才算真正完成：

- 能执行成功
- 能回读关键状态
- 有机器可判断的 verification 结果
- 在批量和部分失败场景下，返回结构仍清晰
