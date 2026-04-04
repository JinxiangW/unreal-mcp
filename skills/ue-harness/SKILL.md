---
name: ue-harness
description: ä½¿ç”¨ `unreal-mcp` æ—¶çš„æœ€å°å·¥ä½œæŒ‡å—ï¼Œæ¶µç›–åŸŸé€‰æ‹©ã€æ‰§è¡ŒåŽç«¯ã€é™é»˜å·¥ä½œæµå’Œäº¤ä»˜è¦æ±‚ã€‚
license: MIT
compatibility: opencode
metadata:
  scope: repo-local
  repo: unreal-mcp
---

## Purpose
å½“ä»»åŠ¡å‘ç”Ÿåœ¨ `D:\unreal-mcp`ï¼Œå¹¶ä¸”æ¶‰åŠ Unreal harness çš„å®žçŽ°ã€æ‰©å±•ã€æµ‹è¯•æˆ–æŽ’éšœæ—¶ï¼Œä¼˜å…ˆä½¿ç”¨è¿™ä»½ skillã€‚

è¿™ä»½ skill åªä¿ç•™æœ€å°å¿…è¦è§„åˆ™ï¼Œä¸é‡å¤å±•å¼€æ‰€æœ‰é•¿æ–‡æ¡£ã€‚

## å…ˆçœ‹ä»€ä¹ˆ
æŒ‰é¡ºåºï¼š

1. `docs/inventory.md`
2. `docs/categories.md`
3. å½“å‰ä»»åŠ¡ç›¸å…³çš„åŸŸæ–‡ä»¶

å¦‚æžœè¦æ”¹è¡Œä¸ºæˆ–æž¶æž„ï¼Œå†çœ‹ï¼š

4. `docs/proposal.md`
5. `docs/commands.md`

å¦‚æžœè¦æµ‹è¯•æˆ–äº¤ä»˜ï¼Œå†çœ‹ï¼š

6. `docs/test-plan.md`
7. `docs/verification.md`
8. `docs/workflow.md`
9. `docs/parallel.md`

## é»˜è®¤æ‰§è¡Œé¡ºåº
å¦‚æžœç”¨æˆ·æ²¡æœ‰ç‰¹åˆ«æŒ‡å®šå…¥å£ï¼Œé»˜è®¤æŒ‰è¿™ä¸ªé¡ºåºæ‰§è¡Œï¼Œä¸è¦è®©ç”¨æˆ·æ¯æ¬¡æ‰‹åŠ¨å†³å®šï¼š

1. å…ˆåˆ¤æ–­ä»»åŠ¡åŸŸï¼š`scene / asset / material / material_graph / diagnostics`
2. ä¼˜å…ˆèµ° `unreal_orchestrator`
3. å¦‚æžœæ˜¯é«˜é£Žé™© live editor æ“ä½œï¼Œå…ˆåšï¼š
   - `get_editor_ready_state`
   - å¿…è¦æ—¶ `wait_for_editor_ready`
4. èƒ½ç”¨ orchestrator çš„ guarded å‘½ä»¤ï¼Œå°±ä¸è¦ç›´æŽ¥æ‰“ raw å·¥å…·
5. åªæœ‰åœ¨ orchestrator è¿˜æ²¡è¦†ç›–è¯¥èƒ½åŠ›æ—¶ï¼Œæ‰ç›´æŽ¥è¿›å…¥å¯¹åº”åŸŸ harness
6. `unreal_backend_tcp` åªä½œä¸ºæœ€åŽçš„ internal/fallback å±‚ï¼Œä¸ä½œä¸ºé»˜è®¤å…¥å£

ç®€å•è¯´ï¼š

- é»˜è®¤å…¥å£ï¼š`unreal_orchestrator`
- é»˜è®¤é¢„æ£€ï¼š`get_editor_ready_state`
- é»˜è®¤ç­‰å¾…ï¼š`wait_for_editor_ready`
- é»˜è®¤ç¦æ­¢ï¼šç›´æŽ¥ä¼˜å…ˆä½¿ç”¨ legacy raw å·¥å…·
- é»˜è®¤ç¦æ­¢ï¼šæ™®é€šä½¿ç”¨åœºæ™¯ä¸‹éšå¼è‡ªåŠ¨å¯åŠ¨ç¼–è¾‘å™¨

## åŸŸé€‰æ‹©
å…ˆæŒ‰é—®é¢˜åŸŸé€‰ç›®å½•ï¼Œä¸è¦ä¸€ä¸Šæ¥å…¨ä»“åº“ä¹±æ”¹ã€‚

- `scene`: `unreal_scene/`
- `asset`: `unreal_asset/`
- `material`: `unreal_material/`
- `material_graph`: `unreal_material_graph/`
- `orchestrator`: `unreal_orchestrator/`
- `diagnostics`: `unreal_diagnostics/`

## å½“å‰åŽç«¯è¾¹ç•Œ
- `unreal_backend_tcp`: internal / fallback onlyï¼Œä¸åº”ç»§ç»­è§†ä¸ºé»˜è®¤ä¸šåŠ¡å…¥å£
- `scene`: ä¼˜å…ˆ `live editor python`
- `asset create/update`: `live editor python`
- `asset import`: `commandlet`
- `material asset/instance/parameter`: åŸºäºŽæ–° `asset` / live editor python
- `material_graph`: ä»åœ¨æ‹†åˆ†ï¼Œæš‚æ—¶ä¸è¦æ··å…¥ `material`

## å½“å‰æ€»æŽ§è¡Œä¸º
- `unreal_orchestrator` å¯¹éƒ¨åˆ†é«˜é£Žé™© live editor å‘½ä»¤å·²è‡ªåŠ¨åš ready preflight
- å¦‚æžœä»»åŠ¡è¦èµ°é«˜é£Žé™©ç¼–è¾‘ï¼Œä¼˜å…ˆé€šè¿‡ orchestratorï¼Œè€Œä¸æ˜¯ç›´æŽ¥ç›²æ‰“åº•å±‚ raw å·¥å…·

## é‡è¯•è§„åˆ™
- åªè¯»ï¼šæœ€å¤š 3 æ¬¡
- å¹‚ç­‰å†™ï¼šæœ€å¤š 2 æ¬¡
- éžå¹‚ç­‰å†™ï¼šé»˜è®¤ä¸è¦è‡ªåŠ¨æ•´æ¡é‡è¯•
- commandletï¼šæœ€å¤šè¡¥é‡è¯• 1 æ¬¡

å¤±è´¥æ—¶ä¸è¦åªè¿”å›žä¸€å¥æŠ¥é”™ï¼Œè‡³å°‘è¦ä¿ç•™ï¼š

- `operation`
- `attempt`
- `max_attempts`
- `error_type`
- `error_message`
- `recommended_action`

## å·¥ä½œè§„åˆ™
### 1. å…ˆé€‰å¯¹æ‰§è¡Œæ¨¡åž‹
- éœ€è¦å½“å‰å…³å¡/Actor/Viewportï¼šç”¨ live editor
- å¯¼å…¥ã€å¤§æ‰¹é‡æ—  UI æ“ä½œï¼šä¼˜å…ˆ commandlet

### 2. ä¸éšä¾¿æ”¹å…±äº«æ ¸å¿ƒ
åŒæ—¶åªèƒ½æœ‰ä¸€ä¸ªä¼šè¯æ”¹è¿™äº›æ–‡ä»¶ï¼š

- `unreal_harness_runtime/python_exec.py`
- `unreal_harness_runtime/commandlet_exec.py`
- `unreal_orchestrator/server.py`
- `unreal_orchestrator/catalog.py`
- `pyproject.toml`

### 3. é«˜å±‚å‘½ä»¤ä¼˜å…ˆ
å¦‚æžœä»»åŠ¡å·²ç»æ˜¯é«˜é¢‘ã€é‡å¤ã€æ˜“é”™å·¥ä½œæµï¼Œä¼˜å…ˆåšé«˜å±‚å‘½ä»¤ï¼Œä¸è¦ç»§ç»­å †è£¸å±žæ€§å†™å…¥ã€‚

### 4. ä¸è¦æŠŠ `material` å’Œ `material_graph` æ··åœ¨ä¸€èµ·
- `material`: èµ„äº§ã€å®žä¾‹ã€å‚æ•°
- `material_graph`: èŠ‚ç‚¹ã€è¿žçº¿ã€å›¾é‡æž„

## æµ‹è¯•ä¸Žäº¤ä»˜
æ¯ä¸ªæ–°åŠŸèƒ½è‡³å°‘åšï¼š

1. ä¸€æ¡æˆåŠŸè·¯å¾„
2. ä¸€æ¡é”™è¯¯è·¯å¾„
3. ä¸€æ¬¡é‡å¤æ‰§è¡Œ
4. ä¸€æ¬¡å¤±è´¥åŽæ¢å¤æ£€æŸ¥

å°½é‡è¡¥è¿™äº›ç»“æžœå­—æ®µï¼š

- `post_state`
- `verification.checks`
- batch çš„ `summary + items`

## é™é»˜å·¥ä½œæµ
é™é»˜å¯åŠ¨ / è‡ªåŠ¨æ‹‰èµ·ç¼–è¾‘å™¨åªç”¨äºŽï¼š

- MCP åŠŸèƒ½å¼€å‘
- MCP å›žå½’æµ‹è¯•
- è‡ªåŠ¨åŒ–éªŒè¯

å¦‚æžœåªæ˜¯æ™®é€šä½¿ç”¨æ—¶å‡ºé”™ï¼Œä¸è¦é»˜è®¤è‡ªåŠ¨å¯åŠ¨æˆ–é‡å¯ç¼–è¾‘å™¨ã€‚
è¿™æ—¶åº”ä¼˜å…ˆï¼š

- è¿”å›žå¤±è´¥ç»“æžœ
- è¿”å›žå½“å‰ ready çŠ¶æ€
- è¿”å›ž `recommended_action`

åªæœ‰åœ¨ MCP å¼€å‘/å›žå½’æµ‹è¯•é‡Œï¼Œæ‰å…è®¸æ˜¾å¼è°ƒç”¨ dev-only å·¥å…·ï¼š

- `dev_launch_editor_and_wait_ready`

å¦‚æžœéœ€è¦è‡ªåŠ¨å¾ªçŽ¯æµ‹è¯•ï¼š

1. å…ˆçœ‹ `docs/workflow.md`
2. éœ€è¦æ´»ç¼–è¾‘å™¨æ—¶é™é»˜å¯åŠ¨ `UnrealEditor.exe`
3. éœ€è¦éš”ç¦»å¯¼å…¥æ—¶ç”¨ `UnrealEditor-Cmd.exe` commandlet
4. å¯åŠ¨åŽå…ˆåš smoke testï¼Œå†åšåŠŸèƒ½æµ‹è¯•

## å®Œæˆå‰è‡ªæ£€
- æ˜¯å¦åªæ”¹äº†å¯¹åº”åŸŸçš„æ–‡ä»¶
- æ˜¯å¦è¯´æ˜Žæ˜¯å¦éœ€è¦é‡å¯ç¼–è¾‘å™¨/é‡ç¼–æ’ä»¶
- æ˜¯å¦è®°å½•å·²çŸ¥é™åˆ¶
- æ˜¯å¦å®Œæˆè‡³å°‘ä¸€æ¡çœŸå®žçŽ¯å¢ƒå›žå½’
- æ˜¯å¦è¯´æ˜Žå½“å‰ç»“æžœæ ¡éªŒçŠ¶æ€

