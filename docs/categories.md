# Harness åˆ†ç±»ç´¢å¼•

è¿™ä»½æ–‡æ¡£ä¸æ˜¯åŠŸèƒ½è¯´æ˜Žï¼Œè€Œæ˜¯ç»™åŽç»­ AI / harness å·¥ç¨‹å¸ˆåšâ€œæœ€å°é˜…è¯»è·¯ç”±â€çš„ç´¢å¼•ã€‚

ç›®æ ‡ï¼š

- é‡åˆ°æŸç±»ä»»åŠ¡æ—¶ï¼Œåªçœ‹å¯¹åº”æ–‡ä»¶
- é‡åˆ°æŸç±»æ•…éšœæ—¶ï¼Œå…ˆæŸ¥å¯¹åº”å±‚çº§
- é¿å…æ¯æ¬¡éƒ½æŠŠæ•´ä¸ªä»“åº“é‡æ–°è¯»ä¸€é

## åˆ†ç±»åŽŸåˆ™

æœ¬ä»“åº“æŒ‰ä¸¤æ¡è½´æ¥ç†è§£ï¼š

1. åˆ†å±‚ï¼šè¯·æ±‚æ˜¯æ€Žä¹ˆä»Ž MCP åˆ° UE æ‰§è¡Œçš„
2. åˆ†åŸŸï¼šå‘½ä»¤å®žé™…åœ¨æ“ä½œä»€ä¹ˆå¯¹è±¡

å»ºè®®å…ˆæŒ‰â€œåˆ†åŸŸâ€å®šä½ï¼Œå†æŒ‰â€œåˆ†å±‚â€æŽ’éšœã€‚

## åˆ†å±‚

### 1. Python MCP å±‚

èŒè´£ï¼š

- æš´éœ² FastMCP server
- å®šä¹‰å¯¹å¤–å·¥å…·é¢
- è´Ÿè´£ TCP è¯·æ±‚å‘é€ä¸ŽåŸºç¡€é”™è¯¯åŒ…è£…

å…³é”®æ–‡ä»¶ï¼š

- `unreal_orchestrator/server.py`
- `unreal_backend_tcp/tools.py`
- `unreal_backend_tcp/connection.py`
- `unreal_backend_tcp/common.py`

ä»€ä¹ˆæ—¶å€™çœ‹è¿™å±‚ï¼š

- OpenCode / MCP æ— æ³•å¯åŠ¨
- å·¥å…·åã€å‚æ•°åã€Python åŒ…å¯¼å…¥æœ‰é—®é¢˜
- æƒ³ç¡®è®¤å¯¹å¤–æš´éœ²äº†å“ªäº›å·¥ä½œæµ

### 2. ä¼ è¾“å±‚

èŒè´£ï¼š

- UE æ’ä»¶ç›‘å¬ TCP
- æ”¶åŒ…ã€å‘åŒ…ã€è¿žæŽ¥ç”Ÿå‘½å‘¨æœŸ

å…³é”®æ–‡ä»¶ï¼š

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/MCPServerRunnable.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/MCPServerRunnable.h`

ä»€ä¹ˆæ—¶å€™çœ‹è¿™å±‚ï¼š

- `Connection closed`
- `Client disconnected`
- UE ç«¯å£ä¸ç›‘å¬
- æ”¶åˆ°è¯·æ±‚ä½†æ²¡æœ‰å›žåŒ…

### 3. æ¡¥æŽ¥åˆ†å‘å±‚

èŒè´£ï¼š

- æŠŠå‘½ä»¤åè·¯ç”±åˆ°å…·ä½“å‘½ä»¤å¤„ç†å™¨
- å®šä¹‰â€œæ’ä»¶çœŸå®žæ”¯æŒå“ªäº›å‘½ä»¤â€

å…³é”®æ–‡ä»¶ï¼š

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/EpicUnrealMCPBridge.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/EpicUnrealMCPBridge.h`

ä»€ä¹ˆæ—¶å€™çœ‹è¿™å±‚ï¼š

- `Unknown command`
- Python æš´éœ²äº†å·¥å…·ï¼Œä½† UE è¿”å›žä¸æ”¯æŒ
- æƒ³ç¡®è®¤æŸä¸ªå‘½ä»¤åˆ°åº•è¢«æ³¨å†Œåˆ°å“ªä¸ªå‘½ä»¤ç»„

### 4. å…±äº«å†™å…¥ / åå°„å·¥å…·å±‚

èŒè´£ï¼š

- é€šç”¨å±žæ€§è¯»å†™
- enum / struct / color / ç»„ä»¶å±žæ€§æ˜ å°„çš„åº•å±‚æ”¯æ’‘
- JSON <-> UObject/FProperty è½¬æ¢

å…³é”®æ–‡ä»¶ï¼š

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPCommonUtils.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPCommonUtils.h`

ä»€ä¹ˆæ—¶å€™çœ‹è¿™å±‚ï¼š

- `Property not found`
- `Unsupported property type`
- struct å†™ä¸è¿›åŽ»
- enum / é¢œè‰² / åå­—å¤§å°å†™å†™å…¥å¼‚å¸¸

### 5. é¢†åŸŸå‘½ä»¤å±‚

èŒè´£ï¼š

- é¢å‘å¯¹è±¡åŸŸåšçœŸå®žä¸šåŠ¡æ“ä½œ
- ä¾‹å¦‚åœºæ™¯ Actorã€æè´¨å›¾ã€Niagaraã€è“å›¾å›¾

å…³é”®æ–‡ä»¶è§â€œåˆ†åŸŸâ€ç« èŠ‚ã€‚

## åˆ†åŸŸ

### A. åœºæ™¯ä¸ŽçŽ¯å¢ƒç¼–è¾‘

è¦†ç›–å†…å®¹ï¼š

- `spawn_actor`
- `delete_actor`
- `get_actors`
- `set_actor_properties`
- `batch_set_actors_properties`
- å…³å¡ä¸Žè§†å£ç›¸å…³å‘½ä»¤
- ç¯å…‰ã€åŽå¤„ç†ã€Actor transformã€ç»„ä»¶å±žæ€§è·¯ç”±

å…³é”®æ–‡ä»¶ï¼š

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPEnvironmentCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPEnvironmentCommands.h`
- å…³è”å…±äº«å±‚ï¼š
  - `EpicUnrealMCPCommonUtils.cpp`
  - `EpicUnrealMCPBridge.cpp`

AI é‡åˆ°è¿™äº›ä»»åŠ¡æ—¶åªçœ‹ï¼š

- åœºæ™¯å¸ƒå…‰
- åŽå¤„ç†ä½“ç§¯ç¼–è¾‘
- æ‰¹é‡ Actor æ‘†æ”¾
- è§†å£æˆªå›¾ / ç›¸æœºæŽ§åˆ¶
- å…³å¡åˆ›å»º / åŠ è½½ / ä¿å­˜

å…¸åž‹é£Žé™©ï¼š

- Actor å±žæ€§ä¸ä¸€å®šåœ¨ Actor æœ¬ä½“ï¼Œè€Œåœ¨ç»„ä»¶ä¸Š
- ç¯å…‰å•ä½å’Œå¼ºåº¦ä¸èƒ½åªå†™ `Intensity`
- `SpotLight` é»˜è®¤ `Stationary`ï¼Œå®¹æ˜“è§¦å‘é‡å å‘Šè­¦
- `PostProcessVolume.Settings` æ˜¯ structï¼Œä¸æ˜¯æ™®é€šå­—æ®µ

### B. èµ„äº§ä¸Žé€šç”¨ç¼–è¾‘å™¨æ“ä½œ

è¦†ç›–å†…å®¹ï¼š

- é€šç”¨èµ„äº§åˆ›å»º/åˆ é™¤
- èµ„äº§å±žæ€§è¯»å†™
- æ‰¹é‡èµ„äº§åˆ›å»º/æ›´æ–°
- çº¹ç† / FBX å¯¼å…¥

å…³é”®æ–‡ä»¶ï¼š

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPEditorCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPEditorCommands.h`

AI é‡åˆ°è¿™äº›ä»»åŠ¡æ—¶åªçœ‹ï¼š

- åˆ›å»ºæè´¨å®žä¾‹ä¹‹å¤–çš„é€šç”¨èµ„äº§
- æ”¹èµ„äº§å±žæ€§
- å¯¼å…¥èµ„æºæ–‡ä»¶

### C. æè´¨ä¸Žè´´å›¾å·¥ä½œæµ

è¦†ç›–å†…å®¹ï¼š

- åˆ›å»ºæè´¨ / æè´¨å‡½æ•° / æè´¨å®žä¾‹
- æž„å»ºæè´¨å›¾
- è¯»å–æè´¨å›¾
- è®¾ç½®æè´¨å®žä¾‹å‚æ•°
- å¯¼å…¥çº¹ç†

å…³é”®æ–‡ä»¶ï¼š

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPMaterialCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPMaterialCommands.h`

AI é‡åˆ°è¿™äº›ä»»åŠ¡æ—¶åªçœ‹ï¼š

- åˆ›å»º `DefaultLit` æè´¨
- è¿žèŠ‚ç‚¹
- åˆ›å»º MI å¹¶è®¾ç½®å‚æ•°

### D. Niagara å·¥ä½œæµ

è¦†ç›–å†…å®¹ï¼š

- è¯»å– Niagara graph
- æ›´æ–° Niagara graph
- è¯»å– emitter
- æ›´æ–° emitter

å…³é”®æ–‡ä»¶ï¼š

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPNiagaraCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPNiagaraCommands.h`

AI é‡åˆ°è¿™äº›ä»»åŠ¡æ—¶åªçœ‹ï¼š

- Niagara system/emitter æ£€æŸ¥
- Niagara å›¾æ“ä½œ

### E. è“å›¾é«˜å±‚ä¿¡æ¯ä¸Žç¼–è¾‘

è¦†ç›–å†…å®¹ï¼š

- è¯»å– blueprint å†…å®¹
- åˆ†æž graph
- Editor Utility Widget ç›¸å…³ info/update

å…³é”®æ–‡ä»¶ï¼š

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPBlueprintCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPBlueprintCommands.h`

AI é‡åˆ°è¿™äº›ä»»åŠ¡æ—¶åªçœ‹ï¼š

- è¯»å– blueprint å…ƒä¿¡æ¯
- åš blueprint å†…å®¹åˆ†æž
- éž graph çº§çš„è“å›¾æ›´æ–°

### F. è“å›¾å›¾ç¼–è¾‘

è¦†ç›–å†…å®¹ï¼š

- åŠ èŠ‚ç‚¹
- è¿žçº¿
- åˆ›å»ºå˜é‡
- è®¾ç½®å˜é‡å±žæ€§
- åˆ›å»ºå‡½æ•°ä¸Žè¾“å…¥è¾“å‡º
- åˆ é™¤èŠ‚ç‚¹ / å‡½æ•°

å…³é”®æ–‡ä»¶ï¼š

- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPBlueprintGraphCommands.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/EpicUnrealMCPBlueprintGraphCommands.h`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/BlueprintGraph/**/*.cpp`
- `RenderingMCP/Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/BlueprintGraph/**/*.h`

AI é‡åˆ°è¿™äº›ä»»åŠ¡æ—¶åªçœ‹ï¼š

- blueprint graph ç»“æž„æ”¹åŠ¨
- è‡ªå®šä¹‰èŠ‚ç‚¹ç®¡ç†
- å‡½æ•° / å˜é‡ / äº‹ä»¶èŠ‚ç‚¹æ“ä½œ

è¯´æ˜Žï¼š

- è¿™æ˜¯æœ€é‡çš„ä¸€ç»„æ–‡ä»¶
- å¦‚æžœä¸æ˜¯ graph çº§ç¼–è¾‘ï¼Œä¸è¦å…ˆè¯»è¿™ç»„

## æŒ‰ä»»åŠ¡è·¯ç”±ï¼šAI æœ€å°é˜…è¯»é›†åˆ

### ä»»åŠ¡ï¼šMCP è¿žä¸ä¸Š / æœ¬åœ° server å¯ä¸æ¥

å…ˆè¯»ï¼š

- `unreal_orchestrator/server.py`
- `unreal_backend_tcp/connection.py`
- `MCPServerRunnable.cpp`

### ä»»åŠ¡ï¼šå·¥å…·æœ‰ï¼Œä½† UE è¿”å›ž `Unknown command`

å…ˆè¯»ï¼š

- `unreal_backend_tcp/tools.py`
- `EpicUnrealMCPBridge.cpp`

### ä»»åŠ¡ï¼šåœºæ™¯ç¯å…‰ / åŽå¤„ç† / Actor ç¼–è¾‘å¤±è´¥

å…ˆè¯»ï¼š

- `EpicUnrealMCPEnvironmentCommands.cpp`
- `EpicUnrealMCPCommonUtils.cpp`
- `EpicUnrealMCPBridge.cpp`

### ä»»åŠ¡ï¼šæè´¨åˆ›å»º / è¿žçº¿æœ‰é—®é¢˜

å…ˆè¯»ï¼š

- `EpicUnrealMCPMaterialCommands.cpp`
- `unreal_backend_tcp/tools.py`

### ä»»åŠ¡ï¼šNiagara æ“ä½œæœ‰é—®é¢˜

å…ˆè¯»ï¼š

- `EpicUnrealMCPNiagaraCommands.cpp`
- `unreal_backend_tcp/tools.py`

### ä»»åŠ¡ï¼šè“å›¾ä¿¡æ¯è¯»å–/æ›´æ–°å¼‚å¸¸

å…ˆè¯»ï¼š

- `EpicUnrealMCPBlueprintCommands.cpp`
- `unreal_backend_tcp/tools.py`

### ä»»åŠ¡ï¼šè“å›¾ graph æ“ä½œå¼‚å¸¸

å…ˆè¯»ï¼š

- `EpicUnrealMCPBlueprintGraphCommands.cpp`
- `Commands/BlueprintGraph/**/*.cpp`

## æŒ‰æ•…éšœè·¯ç”±ï¼šAI æœ€å°é˜…è¯»é›†åˆ

### ç—‡çŠ¶ï¼š`Unknown command`

ä¼˜å…ˆçœ‹ï¼š

- `EpicUnrealMCPBridge.cpp`

å¸¸è§æ ¹å› ï¼š

- Python ä¾§å·²æš´éœ²ï¼Œbridge æœªæ³¨å†Œ

### ç—‡çŠ¶ï¼š`Property not found`

ä¼˜å…ˆçœ‹ï¼š

- `EpicUnrealMCPEnvironmentCommands.cpp`
- `EpicUnrealMCPCommonUtils.cpp`

å¸¸è§æ ¹å› ï¼š

- å±žæ€§åœ¨ç»„ä»¶ä¸Šï¼Œä¸åœ¨ Actor ä¸Š
- å¤§å°å†™ / å‘½åé£Žæ ¼ä¸ä¸€è‡´
- éœ€è¦ä¸“ç”¨ setterï¼Œè€Œä¸æ˜¯æ™®é€šå±žæ€§å†™å…¥

### ç—‡çŠ¶ï¼š`Unsupported property type: StructProperty`

ä¼˜å…ˆçœ‹ï¼š

- `EpicUnrealMCPCommonUtils.cpp`

å¸¸è§æ ¹å› ï¼š

- ç¼ºå°‘ struct é€’å½’å†™å…¥
- åŽå¤„ç† `Settings` è¿™ç±»å¤§ struct æœªåšç‰¹åˆ¤

### ç—‡çŠ¶ï¼š`Connection closed` / æ²¡æœ‰å›žåŒ…

ä¼˜å…ˆçœ‹ï¼š

- `MCPServerRunnable.cpp`
- `EpicUnrealMCPBridge.cpp`
- å½“å‰è¿è¡Œå®žä¾‹å¯¹åº”çš„ UE æ—¥å¿—

å¸¸è§æ ¹å› ï¼š

- è¯·æ±‚æ‰§è¡Œè¿‡ç¨‹ä¸­æœªæ­£ç¡®æž„é€ å“åº”
- å½“å‰æ—¥å¿—ä¸æ˜¯å½“å‰è¿è¡Œå®žä¾‹çš„æ—¥å¿—

## å½“å‰å·²çŸ¥é«˜é£Žé™©åŒº

è¿™äº›åœºæ™¯è¯·ä¼˜å…ˆæŠŠ AI è·¯ç”±åˆ°â€œåœºæ™¯ä¸ŽçŽ¯å¢ƒç¼–è¾‘â€åˆ†ç±»ï¼Œä¸è¦åªé é€šç”¨å±žæ€§å†™å…¥æŽ¨æ–­ï¼š

- ç¯å…‰å¼ºåº¦å•ä½
- `SpotLight` æœå‘
- `Mobility`
- `LightColor`
- `PostProcessVolume.Settings`
- æ‰¹é‡ Actor transform + properties æ··åˆå†™å…¥

## ç»´æŠ¤å»ºè®®

åŽç»­å¦‚æžœæ–°å¢žå‘½ä»¤ï¼Œè‡³å°‘åŒæ­¥æ›´æ–°ä¸¤å¤„ï¼š

1. `unreal_backend_tcp/tools.py`
2. `docs/categories.md`

å¦‚æžœæ˜¯ UE ä¾§æ–°å¢žå‘½ä»¤ï¼Œè¿˜è¦åŒæ­¥ç¡®è®¤ï¼š

3. `EpicUnrealMCPBridge.cpp`

è¿™ä»½æ–‡æ¡£çš„ç›®æ ‡ä¸æ˜¯â€œå®Œæ•´â€ï¼Œè€Œæ˜¯ä¿è¯ AI åœ¨å¤§å¤šæ•°ä»»åŠ¡é‡Œèƒ½å…ˆè¯»æœ€å°‘çš„æ­£ç¡®æ–‡ä»¶ã€‚


