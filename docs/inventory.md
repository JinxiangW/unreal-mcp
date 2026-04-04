# åŠŸèƒ½æ¸…å•æ€»è§ˆ

è¿™ä»½æ–‡æ¡£åˆ—å‡ºå½“å‰ä»“åº“é‡Œçš„åŠŸèƒ½å…¨æ™¯ï¼Œè€Œä¸æ˜¯åªåˆ—é«˜å±‚å‘½ä»¤æˆ–æž¶æž„æ–¹å‘ã€‚

åˆ†ä¸ºä¸‰ç±»ï¼š

- å½“å‰å¯ç”¨çš„ internal/backend MCP åŠŸèƒ½
- æ–° harness å·²è¿ç§»å¹¶å¯ç”¨çš„åŠŸèƒ½
- å·²è§„åˆ’ä½†å°šæœªçœŸæ­£å®žçŽ°çš„åŠŸèƒ½

## æœ¯è¯­è¯´æ˜Ž

### çœŸå®žçŽ¯å¢ƒå›žå½’

æ–‡æ¡£é‡Œä¹‹å‰å†™çš„â€œçœŸå®žå›žå½’â€ï¼Œè¿™é‡Œç»Ÿä¸€æ˜Žç¡®æˆâ€œçœŸå®žçŽ¯å¢ƒå›žå½’â€ã€‚

å«ä¹‰ï¼š

- ä¸æ˜¯åªåšè¯­æ³•æ£€æŸ¥
- ä¸æ˜¯åªåš mock
- ä¸æ˜¯åªçœ‹ä»£ç è·¯å¾„æŽ¨æ–­
- è€Œæ˜¯åœ¨çœŸå®ž UE çŽ¯å¢ƒã€çœŸå®žé¡¹ç›®ã€çœŸå®žèµ„äº§æˆ–çœŸå®žå…³å¡ä¸Šä¸‹æ–‡é‡Œæ‰§è¡Œä¸€æ¬¡åŠŸèƒ½ï¼Œå†æ£€æŸ¥ç»“æžœ

è¿™ä¸ªè¯´æ³•æ¥è‡ªå¸¸è§å·¥ç¨‹æœ¯è¯­ï¼š

- `regression test / å›žå½’æµ‹è¯•`

è¿™é‡ŒåŠ ä¸Šâ€œçœŸå®žçŽ¯å¢ƒâ€ä¸‰ä¸ªå­—ï¼Œæ˜¯ä¸ºäº†å’Œä¸‹é¢å‡ ç±»åŒºåˆ†å¼€ï¼š

- è¯­æ³•æ£€æŸ¥
- å¯¼å…¥æ£€æŸ¥
- å•å…ƒçº§æ£€æŸ¥
- çº¯é™æ€ä»£ç æ£€æŸ¥

## çŠ¶æ€å­—æ®µè¯´æ˜Ž

- `çŠ¶æ€`
  - `å¯ç”¨`: å½“å‰å¯ä»¥ç›´æŽ¥ä½¿ç”¨
  - `éƒ¨åˆ†å¯ç”¨`: å·²æœ‰éƒ¨åˆ†èƒ½åŠ›æˆ–ä¾èµ–ç‰¹å®šå‰æ
  - `è§„åˆ’ä¸­`: è¿˜æœªçœŸæ­£å®žçŽ°
- `æ‰§è¡ŒåŽç«¯`
  - `internal tcp`
  - `live editor python`
  - `commandlet`
  - `mixed`
- `é»˜è®¤å…¥å£`
  - `orchestrator`
  - `domain harness`
  - `commandlet only`
  - `internal backend`
  - `internal/debug`
- `éªŒè¯çŠ¶æ€`
  - `å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’`
  - `ä»…åšåŸºç¡€éªŒè¯`
  - `æœªéªŒè¯`
- `ç»“æžœæ ¡éªŒçŠ¶æ€`
  - `å·²æŽ¥å…¥`
  - `æœªæŽ¥å…¥`
  - `éƒ¨åˆ†æŽ¥å…¥`
  - `ç›®æ ‡è¦æ±‚`

## 1. Internal / `unreal_backend_tcp` å½“å‰å¯ç”¨åŠŸèƒ½

è¿™äº›æ˜¯å½“å‰åº•å±‚ä»ç„¶å¯ç›´æŽ¥è°ƒç”¨çš„èƒ½åŠ›é¢ã€‚

ä½†å®ƒçš„å®šä½åº”ç†è§£ä¸ºï¼š

- internal
- fallback
- è¿ç§»æœŸå…¼å®¹å±‚

è€Œä¸æ˜¯åŽç»­é»˜è®¤æŽ¨èç›´æŽ¥ä½¿ç”¨çš„ä¸»è¦ä¸šåŠ¡å…¥å£ã€‚

### Asset

- `get_assets`
- `get_asset_properties`
- `create_asset`
- `set_asset_properties`
- `delete_asset`
- `batch_create_assets`
- `batch_set_assets_properties`
- `read_result_handle`
- `release_result_handle`

### Level / Viewport

- `get_current_level`
- `create_level`
- `load_level`
- `save_current_level`
- `get_viewport_camera`
- `set_viewport_camera`
- `get_viewport_screenshot`

### Actor / Scene

- `get_actors`
- `get_actor_properties`
- `spawn_actor`
- `set_actor_properties`
- `delete_actor`
- `batch_spawn_actors`
- `batch_delete_actors`
- `batch_set_actors_properties`

### Import

- `import_texture`
- `import_fbx`

### Material / Material Graph

- `build_material_graph`
- `get_material_graph`

### Niagara

- `get_niagara_graph`
- `update_niagara_graph`
- `get_niagara_emitter`
- `update_niagara_emitter`
- `get_niagara_compiled_code`
- `get_niagara_particle_attributes`

### Blueprint Info / Content

- `get_blueprint_info`
- `update_blueprint`
- `read_blueprint_content`
- `analyze_blueprint_graph`

è¯´æ˜Žï¼š

- å½“å‰ raw å·¥å…·å·²åš wrapper å±‚ token ä¼˜åŒ–
- æŸ¥è¯¢ç±»é»˜è®¤æ”¯æŒ `summary_only / fields / limit`
- å›¾ç±»å’Œ Blueprint å†…å®¹é»˜è®¤æ‘˜è¦è¿”å›ž
- å¤§ç»“æžœæ”¯æŒ `saved_to` ä¸Ž `result_handle`

### Blueprint Graph

- `blueprint_graph_command`

æ”¯æŒçš„å›¾å‘½ä»¤ï¼š

- `add_blueprint_node`
- `connect_nodes`
- `create_variable`
- `set_blueprint_variable_properties`
- `add_event_node`
- `delete_node`
- `set_node_property`
- `create_function`
- `add_function_input`
- `add_function_output`
- `delete_function`
- `rename_function`

## 2. æ–° Harness å½“å‰å·²å®žçŽ°åŠŸèƒ½

é»˜è®¤ä½¿ç”¨è§„åˆ™ï¼š

- å¦‚æžœç”¨æˆ·æˆ–ä¼šè¯æ²¡æœ‰ç‰¹åˆ«æŒ‡å®šå…¥å£ï¼Œé»˜è®¤æŒ‰ç…§â€œé»˜è®¤å…¥å£â€è¿™ä¸€åˆ—æ¥è°ƒç”¨
- ç›®å‰å¤§å¤šæ•°é«˜é£Žé™©åŠŸèƒ½éƒ½åº”ä¼˜å…ˆèµ° `orchestrator`

### çŠ¶æ€çŸ©é˜µ

| åŸŸ | åŠŸèƒ½ | çŠ¶æ€ | æ‰§è¡ŒåŽç«¯ | é»˜è®¤å…¥å£ | éªŒè¯çŠ¶æ€ | ç»“æžœæ ¡éªŒçŠ¶æ€ |
| --- | --- | --- | --- | --- | --- | --- |
| orchestrator | `get_harness_domains` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| orchestrator | `get_domain_design` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| orchestrator | `route_harness_task` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| scene | `get_scene_harness_info` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| scene | `get_scene_backend_status` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| scene | `query_scene_actors` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| scene | `query_scene_lights` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| scene | `set_scene_light_intensity` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| scene | `create_spot_light_ring` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| scene | `aim_actor_at` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| scene | `set_post_process_overrides` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| scene | `spawn_actor_with_defaults` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| scene | `inspect_scene_python_enums` | å¯ç”¨ | live editor python | domain harness | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| asset | `get_asset_harness_info` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| asset | `query_assets_summary` | å¯ç”¨ | internal tcp wrapper | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| asset | `ensure_folder` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| asset | `create_asset_with_properties` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| asset | `ensure_asset_with_properties` | å¯ç”¨ | mixed | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| asset | `duplicate_asset_with_overrides` | å¯ç”¨ | mixed | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| asset | `move_asset_batch` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| asset | `update_asset_properties` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| asset | `import_texture_asset` | å¯ç”¨ | commandlet | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| asset | `import_fbx_asset` | å¯ç”¨ | commandlet | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material | `get_material_harness_info` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material | `create_material_asset` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material | `create_material_instance_asset` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material | `update_material_instance_properties` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material | `update_material_instance_parameters_and_verify` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material | `get_material_instance_parameter_names` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material | `set_material_instance_scalar_parameter` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material | `set_material_instance_vector_parameter` | å¯ç”¨ | live editor python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material | `set_material_instance_texture_parameter` | å¯ç”¨ | live editor python | orchestrator | ä»…åšåŸºç¡€éªŒè¯ | å·²æŽ¥å…¥ |
| material_graph | `get_material_graph_harness_info` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material_graph | `analyze_material_graph` | å¯ç”¨ | internal tcp wrapper | domain harness | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material_graph | `create_material_graph_recipe` | å¯ç”¨ | internal tcp wrapper | domain harness | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| material_graph | `connect_material_nodes` | å¯ç”¨ | internal tcp wrapper | domain harness | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| diagnostics | `get_harness_health` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| diagnostics | `get_runtime_policy` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| diagnostics | `get_transport_port_status` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| diagnostics | `get_unreal_python_status` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| diagnostics | `get_editor_process_status` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| diagnostics | `get_commandlet_runtime_status` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| diagnostics | `get_editor_ready_state` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| diagnostics | `wait_for_editor_ready` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| diagnostics | `get_token_usage_summary` | å¯ç”¨ | python | orchestrator | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |
| diagnostics | `dev_launch_editor_and_wait_ready` | å¯ç”¨ | python | internal/debug | å·²åšçœŸå®žçŽ¯å¢ƒå›žå½’ | å·²æŽ¥å…¥ |

### Orchestrator

ç›®å½•ï¼š`unreal_orchestrator/`

å·²å®žçŽ°ï¼š

- `get_harness_domains`
- `get_domain_design`
- `route_harness_task`

### Scene

ç›®å½•ï¼š`unreal_scene/`

çŠ¶æ€ï¼šå·²å¼€å§‹åˆ‡åˆ° UE Python

å·²å®žçŽ°ï¼š

- `get_scene_harness_info`
- `get_scene_backend_status`
- `query_scene_actors`
- `query_scene_lights`
- `set_scene_light_intensity`
- `create_spot_light_ring`
- `aim_actor_at`
- `set_post_process_overrides`
- `spawn_actor_with_defaults`
- `inspect_scene_python_enums`

å¤‡æ³¨ï¼š

- èµ° `run_python` åˆ°ç¼–è¾‘å™¨å†… Python
- å·²æœ‰çœŸå®žçŽ¯å¢ƒå›žå½’

### Asset

ç›®å½•ï¼š`unreal_asset/`

çŠ¶æ€ï¼šå·²åˆ‡åˆ°æ··åˆæ‰§è¡Œæ¨¡åž‹

å·²å®žçŽ°ï¼š

- `get_asset_harness_info`
- `query_assets_summary`
- `ensure_asset_with_properties`
- `create_asset_with_properties`
- `update_asset_properties`
- `import_texture_asset`
- `import_fbx_asset`

æ‰§è¡Œæ¨¡åž‹ï¼š

- `create/update` èµ° live editor `run_python`
- `import` èµ°ç‹¬ç«‹ commandlet

### Material

ç›®å½•ï¼š`unreal_material/`

çŠ¶æ€ï¼šèµ„äº§/å®žä¾‹/å‚æ•°å±‚å·²æŽ¥ä¸Šæ–°é“¾è·¯

å·²å®žçŽ°ï¼š

- `get_material_harness_info`
- `create_material_asset`
- `create_material_instance_asset`
- `update_material_instance_properties`
- `update_material_instance_parameters_and_verify`
- `get_material_instance_parameter_names`
- `set_material_instance_scalar_parameter`
- `set_material_instance_vector_parameter`
- `set_material_instance_texture_parameter`

### Material Graph

ç›®å½•ï¼š`unreal_material_graph/`

çŠ¶æ€ï¼šå·²è¿›å…¥æœ€å°å¯ç”¨é˜¶æ®µ

å½“å‰å·²å®žçŽ°ï¼š

- `get_material_graph_harness_info`
- `analyze_material_graph`
- `create_material_graph_recipe`
- `connect_material_nodes`

### Diagnostics

ç›®å½•ï¼š`unreal_diagnostics/`

å½“å‰å·²å®žçŽ°ï¼š

- `get_harness_health`
- `get_runtime_policy`
- `get_editor_ready_state`
- `wait_for_editor_ready`
- `get_token_usage_summary`
- `get_transport_port_status`
- `get_unreal_python_status`
- `get_editor_process_status`
- `get_commandlet_runtime_status`
- `dev_launch_editor_and_wait_ready`ï¼ˆinternal/debugï¼‰

## 3. å·²è§„åˆ’ä½†å°šæœªå®Œæ•´å®žçŽ°çš„åŠŸèƒ½

### Scene

- `create_three_point_lighting`

### Asset

- æ›´å®Œæ•´çš„æè´¨å®žä¾‹å‚æ•°å±‚è¿”å›žç»“æž„

### Material Graph

- å›¾é‡æž„

### Orchestrator

- çœŸæ­£çš„åŸŸçº§è°ƒåº¦
- ç»Ÿä¸€é”™è¯¯æ¨¡åž‹
- ç»Ÿä¸€ç»“æžœåŒ…è£…

### Diagnostics

- æ›´ç»†çš„é”™è¯¯åˆ†ç±»ä¸ŽæŒä¹…åŒ–è¯Šæ–­

## 4. çŽ°é˜¶æ®µæœ€é‡è¦çš„è¾¹ç•Œ

### å·²é€‚åˆä½¿ç”¨çš„æ–°é“¾è·¯

- `scene` çš„é«˜å±‚å‘½ä»¤ä¸Ž compact æŸ¥è¯¢
- `asset` çš„ create/update/import
- `asset` çš„ ensure/query å·¥ä½œæµ
- `material` çš„èµ„äº§/å®žä¾‹/å‚æ•°å±‚

### ä»ä¾èµ–æ—§èƒ½åŠ›é¢æˆ–å°šæœªæ‹†åˆ†å®Œæˆ

- `material graph`
- `niagara`
- `blueprint info`
- `blueprint graph`

## 5. å»ºè®®é˜…è¯»é¡ºåº

å¦‚æžœåªæƒ³çœ‹â€œçŽ°åœ¨åˆ°åº•èƒ½ç”¨ä»€ä¹ˆâ€ï¼š

1. å…ˆçœ‹æœ¬æ–‡ä»¶ `inventory.md`
2. å†çœ‹ `commands.md`
3. å†çœ‹ `categories.md`

