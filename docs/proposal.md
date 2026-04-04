# æ–° Harness æž¶æž„æ–¹æ¡ˆ v0.1

## ç›®æ ‡

è¿™ç‰ˆæ–¹æ¡ˆæœåŠ¡ä¸‰ä¸ªç›®æ ‡ï¼š

1. ç¨³å®šä¼˜å…ˆ
2. å¯ç»´æŠ¤æ€§ä¼˜å…ˆ
3. ä¿æŒä¸€ä¸ªå…¨å±€å¯æŽ§å…¥å£ï¼Œä½†å†…éƒ¨æŒ‰é—®é¢˜åŸŸæ‹†åˆ†

## æ ¸å¿ƒç»“è®º

ä¸å»ºè®®ç»§ç»­ç»´æŠ¤ä¸€ä¸ªâ€œå¤§è€Œå…¨â€çš„å•ä½“ C++ å±žæ€§è·¯ç”±åž‹ harnessã€‚

ä¹Ÿä¸å»ºè®®ç»§ç»­æŠŠ `unreal_backend_tcp` ä½œä¸ºé»˜è®¤å¯¹å¤–ä¸šåŠ¡å…¥å£ã€‚

å®ƒåº”é€æ­¥é™çº§ä¸ºï¼š

- internal backend
- compatibility layer
- fallback path

å»ºè®®æ”¹ä¸ºï¼š

- å¯¹å¤–ï¼šä¸€ä¸ªæ€»æŽ§å…¥å£ `unreal-orchestrator`
- å¯¹å†…ï¼šå¤šä¸ªæŒ‰é—®é¢˜åŸŸæ‹†åˆ†çš„å­ harness
- æ‰§è¡Œå±‚ï¼š`Scene / Asset / Material Asset` ä¼˜å…ˆåˆ‡åˆ° UE Python
- ä¿ç•™å±‚ï¼šBlueprint Graphã€éƒ¨åˆ† Niagaraã€ä¼ è¾“ä¸Žæ¡¥æŽ¥ä¿ç•™åœ¨ C++ æ’ä»¶

## æŽ¨èç»“æž„

### å¯¹å¤–å…¥å£

- `unreal-orchestrator`

èŒè´£ï¼š

- è¯†åˆ«ä»»åŠ¡ç±»åž‹
- è·¯ç”±åˆ°å­ harness
- åš preflight
- ç»Ÿä¸€é”™è¯¯æ¨¡åž‹
- æ±‡æ€»éªŒè¯ç»“æžœ

### å­ harness åˆ—è¡¨

- `unreal-scene`
- `unreal-asset`
- `unreal-material`
- `unreal-material-graph`
- `unreal-niagara`
- `unreal-blueprint-info`
- `unreal-blueprint-graph`
- `unreal-diagnostics`

## æ¯ä¸ªå­ harness çš„èŒè´£è¾¹ç•Œ

### 1. unreal-scene

åŽç«¯ï¼šUE Python

è¦†ç›–ï¼š

- åœºæ™¯ç¯å…‰
- åŽå¤„ç†
- Actor åˆ›å»º / åˆ é™¤ / æ‰¹é‡æ‘†æ”¾
- transform
- å…³å¡æ“ä½œ
- è§†å£æˆªå›¾ä¸Žç›¸æœº

å»ºè®®æä¾›é«˜å±‚å‘½ä»¤ï¼Œè€Œä¸æ˜¯è£¸å±žæ€§å†™å…¥ï¼š

- `create_spot_light_ring`
- `aim_actor_at`
- `set_light_intensity`
- `set_post_process_overrides`
- `spawn_actor_with_defaults`

### 2. unreal-asset

åŽç«¯ï¼šUE Python

è¦†ç›–ï¼š

- é€šç”¨èµ„äº§ CRUD
- è·¯å¾„æŸ¥è¯¢
- èµ„äº§å±žæ€§ä¿®æ”¹
- æ‰¹é‡æ“ä½œ
- å¯¼å…¥

### 3. unreal-material

åŽç«¯ï¼šUE Python

è¦†ç›–ï¼š

- æè´¨åˆ›å»º
- æè´¨å®žä¾‹åˆ›å»º
- å‚æ•°è®¾ç½®
- æè´¨åŸºç¡€å±žæ€§

### 4. unreal-material-graph

åŽç«¯ï¼šC++ ä¸»ï¼Œå¿…è¦æ—¶ç”± Python åšé«˜å±‚ç¼–æŽ’

è¦†ç›–ï¼š

- æè´¨èŠ‚ç‚¹åˆ›å»º
- è¿žçº¿
- æè´¨å›¾æž„å»º
- æè´¨å›¾è¯»å–ä¸Žåˆ†æž
- å¤æ‚å›¾é‡æž„

åŽŸå› ï¼š

- é•¿æœŸçœ‹ä¼šèµ°å¤æ‚æè´¨å›¾ç¼–è¾‘
- ä¸å»ºè®®ä¸€å¼€å§‹æŠŠå¤æ‚ graph editing å®Œå…¨æŠ¼åœ¨ UE Python ä¸Š

### 5. unreal-niagara

åŽç«¯ï¼šæ··åˆ

è¦†ç›–ï¼š

- emitter / graph è¯»å–
- å¸¸è§å›¾ç¼–è¾‘
- å¤æ‚èƒ½åŠ›å…ˆä¿ç•™ C++

### 6. unreal-blueprint-info

åŽç«¯ï¼šUE Python

è¦†ç›–ï¼š

- è“å›¾ç»“æž„è¯»å–
- å†…å®¹å¿«ç…§
- åˆ†æžä¸Žæ±‡æ€»

### 7. unreal-blueprint-graph

åŽç«¯ï¼šC++ æ’ä»¶ä¸»å¯¼

è¦†ç›–ï¼š

- èŠ‚ç‚¹å¢žåˆ 
- è¿žçº¿
- å˜é‡
- å‡½æ•°
- äº‹ä»¶å›¾ä¿®æ”¹

åŽŸå› ï¼š

- è¿™æ˜¯é«˜å¤æ‚åº¦å›¾ç¼–è¾‘åŸŸ
- ä¸å»ºè®®ç¬¬ä¸€é˜¶æ®µè½¬åˆ° Python

### 8. unreal-diagnostics

åŽç«¯ï¼šæ··åˆ

è¦†ç›–ï¼š

- èƒ½åŠ›æŽ¢æµ‹
- UE æ—¥å¿—æ£€æŸ¥
- å‘½ä»¤æ³¨å†Œä¸€è‡´æ€§æ£€æŸ¥
- å›žå½’éªŒè¯

## ä¸ºä»€ä¹ˆ Scene / Asset / Material Asset å…ˆè½¬ UE Python

### Scene

å½“å‰é—®é¢˜æš´éœ²å‡ºï¼š

- Actor / Component / Struct æ¨¡åž‹ä¸é€‚åˆé•¿æœŸé é€šç”¨å±žæ€§åå°„ç¡¬å†™
- åœºæ™¯ç¯å…‰å’ŒåŽå¤„ç†å¤©ç„¶æ˜¯ç¼–è¾‘å™¨è¯­ä¹‰é—®é¢˜ï¼Œä¸æ˜¯ç®€å• JSON å†™å±žæ€§é—®é¢˜

### Asset

- èµ„äº§å·¥ä½œæµå’Œ EditorAssetLibrary / AssetTools è´´å¾—æ›´è¿‘
- Python ä¾§ç»´æŠ¤æˆæœ¬æ›´ä½Ž

### Material

- æè´¨èµ„äº§å’Œæè´¨å®žä¾‹ç®¡ç†é€‚åˆ UE Python
- ä½†å¤æ‚æè´¨å›¾ç¼–è¾‘åº”æ‹†åˆ° `unreal-material-graph`
- ä¸å†æŠŠâ€œæè´¨èµ„äº§ç®¡ç†â€å’Œâ€œå¤æ‚æè´¨å›¾ç¼–è¾‘â€æ··æˆä¸€ä¸ªåŸŸ

## C++ æ’ä»¶åº”ä¿ç•™ä»€ä¹ˆ

- TCP æœåŠ¡
- å‘½ä»¤æ³¨å†Œå’Œ capability registry
- Blueprint Graph ç¼–è¾‘
- Python ä¸è¶³çš„åº•å±‚èƒ½åŠ›
- ä¸€è‡´çš„å“åº”æ ¼å¼å’Œé”™è¯¯ç 

## å»ºè®®æ¸…ç†çš„æ—§å®žçŽ°

### ä¼˜å…ˆæ¸…ç†

- åœºæ™¯ç¼–è¾‘ç›¸å…³çš„é«˜å±‚å±žæ€§è·¯ç”±
- é€šç”¨ `set_actor_properties` ä¸­æ‰¿æ‹…ä¸šåŠ¡è¯­ä¹‰çš„éƒ¨åˆ†
- å¤šå¤„æ‰‹å·¥åŒæ­¥çš„å‘½ä»¤è¡¨

### æš‚æ—¶ä¿ç•™

- ä¼ è¾“å±‚
- bridge
- Blueprint Graph
- Niagara çŽ°æœ‰æ ¸å¿ƒå®žçŽ°
- `unreal_backend_tcp` ä½œä¸º internal/fallback å±‚

## é”™è¯¯æ¨¡åž‹å»ºè®®

ç»Ÿä¸€åˆ†ä¸ºï¼š

- `transport_error`
- `protocol_error`
- `capability_error`
- `validation_error`
- `runtime_error`
- `partial_apply`

è¿™æ ·åŽç»­ AI ä¸ä¼šæŠŠæ‰€æœ‰å¤±è´¥éƒ½è¯¯åˆ¤ä¸ºâ€œè¿žæŽ¥æ–­å¼€â€ã€‚

## ç¬¬ä¸€é˜¶æ®µè½åœ°é¡ºåº

### Phase 1

- å»ºç«‹ `unreal-orchestrator`
- å»ºç«‹æ–°çš„èƒ½åŠ›åˆ†ç±»å’Œè·¯ç”±è¡¨
- ä¿ç•™æ—§å®žçŽ°ä½œä¸º fallback

### Phase 2

- é‡å†™ `unreal-scene`
- é‡å†™ `unreal-asset`
- é‡å†™ `unreal-material`
- è®¾è®¡ `unreal-material-graph` çš„ç‹¬ç«‹èƒ½åŠ›é¢

### Phase 3

- é€æ­¥æ”¶ç¼©æ—§ C++ é«˜å±‚å±žæ€§å†™å…¥é€»è¾‘
- è®© scene / asset / material asset é»˜è®¤åªèµ° UE Python
- ä¿ç•™ material graph çš„ C++ ä¸»å®žçŽ°

### Phase 4

- æ¢³ç† Niagara è¾¹ç•Œ
- æ•´ç† Blueprint Graph å•ç‹¬èƒ½åŠ›é¢
- ç»Ÿä¸€å›žå½’æµ‹è¯•å’Œ diagnostics

## ç›®å½•å»ºè®®

å»ºè®®æœªæ¥æ¼”åŒ–åˆ°ç±»ä¼¼ç»“æž„ï¼š

```text
unreal-mcp/
  unreal_orchestrator/
  unreal_scene/
  unreal_asset/
  unreal_material/
  unreal_material_graph/
  unreal_niagara/
  unreal_blueprint_info/
  unreal_blueprint_graph/
  unreal_diagnostics/
  RenderingMCP/Plugins/UnrealMCP/
  docs/
```

## å½“å‰å»ºè®®

ä¸‹ä¸€æ­¥æœ€å€¼å¾—åšçš„æ˜¯ï¼š

1. å…ˆå®šä¹‰ orchestrator çš„è¾“å…¥/è¾“å‡ºåè®®
2. ç«‹åˆ»æŠ½å‡º `scene` å­ harness çš„ UE Python ç‰ˆæœ¬
3. å†æŠŠ `asset` å’Œ `material` è·Ÿä¸Š
4. å•ç‹¬å®šä¹‰ `material-graph`ï¼Œä¸è¦æ··å…¥æ™®é€šæè´¨èµ„äº§æµ

è¿™æ ·æœ€çŸ­è·¯å¾„å°±èƒ½æŠŠæœ€å®¹æ˜“å‡ºé—®é¢˜çš„ä¸€æ‰¹ç¼–è¾‘å·¥ä½œæµä»Žæ—§ C++ å±žæ€§è·¯ç”±ä¸­æ‹¿å‡ºæ¥ã€‚

