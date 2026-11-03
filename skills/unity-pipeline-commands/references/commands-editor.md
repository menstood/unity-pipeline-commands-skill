# Editor, build, settings, packages, runtime commands

Same conventions as commands-content.md: **(req)** = required; standard `confirm`/`dry_run` semantics.

## Baking

All bakes are async: trigger returns immediately → poll the matching `*_status` (returns `idle | baking | completed`) → `cancel_*` to abort. Clears are destructive (`confirm:true`, not undoable).

### Lighting
| Command | Params / Notes |
|---|---|
| `bake_lighting` | `confirm` (recommended true — overwrites lightmap data), `dry_run` (validate bakeable scene + return current lighting settings). Uses `Lightmapping.BakeAsync()` |
| `lighting_bake_status` | → `idle | baking | completed` |
| `cancel_lighting_bake` | `Lightmapping.Cancel()` |
| `clear_baked_lighting` | `confirm` (must be true), `include_disk_cache` (default false; also `Lightmapping.ClearDiskCache()`), `dry_run` |
| `get_lighting_settings` | Lightmapper, bounces, resolution, directional mode, AO, etc. Returns `LightingSettingsResult` |
| `set_lighting_settings` | `settings` (req, JSON subset, same names/enums as get), `dry_run`. Returns `{ applied[], unknown[] }` |

### NavMesh (legacy)
| Command | Params / Notes |
|---|---|
| `bake_navmesh` | `confirm` (parity only, not required), `dry_run`. Uses `UnityEditor.AI.NavMeshBuilder` |
| `navmesh_bake_status` / `cancel_navmesh_bake` | |
| `clear_navmesh` | `confirm` (must be true), `dry_run` |
| `get_navmesh_settings` / `set_navmesh_settings` | agentRadius/Height/Slope/Climb, minRegionArea, voxelSize. set: `settings` (req), `dry_run` → `{ applied[], unknown[] }` |
| `bake_navmesh_surfaces` | NavMeshSurface components (AI Navigation package). v1 stub: `package_not_found` if package absent. |

### Occlusion culling
| Command | Params / Notes |
|---|---|
| `bake_occlusion_culling` | `smallest_occluder` (m), `smallest_hole` (m), `backface_threshold` (1–100, lower trims more), `confirm` (parity, not required), `dry_run`. `StaticOcclusionCulling.GenerateInBackground()` |
| `occlusion_bake_status` / `cancel_occlusion_bake` | |
| `clear_occlusion_culling` | `confirm` (must be true), `dry_run` |

## Search & selection (read-only / non-destructive, main thread)

| Command | Params / Notes |
|---|---|
| `get_selection` | Current Editor selection as structured identities. Returns `SelectionResult` |
| `set_selection` | `instance_ids` (scene/loaded object IDs) and/or `paths` (asset paths). Returns `SelectionResult` |
| `search` | `query` (req, Unity Search syntax: `t:Material`, `p: my asset`, `h: Main Camera`), `limit` (default 50, cap 200). Returns `SearchResult` |

## Capture

| Command | Params / Notes |
|---|---|
| `capture_game_view` | `width` (default 1280, cap 4096), `height` (default 720, cap 4096), `camera` (name; default Camera.main or first enabled), `save_path` (project-relative). Returns base64 PNG in `CaptureResult` |
| `capture_scene_view` | `width`, `height`, `save_path`. Active Scene View → PNG (base64) |
| `capture_editor_element` | `window` (req, EditorWindow type name e.g. `InspectorWindow`, or title), `selector` (req, UI Toolkit: `#name`, `.class`, type, descendant/child chains, `:checked`/`:hover`/`:focus`/`:active`/`:enabled`/`:disabled`/`:not(...)`), `output` (default timestamped under `/Temp/pipeline-screenshots/`). **Unity 6000.7+ only.** Returns `CaptureElementResponse` (path + base64) |
| `capture_runtime_element` | `panel` (PanelSettings asset or host GO name; optional if exactly one panel), `selector` (req), `output` (default under `Application.persistentDataPath`). RuntimeOnly, **Unity 6000.7+ only** |

Also `screenshot` under Editor lifecycle below (simpler: view name → PNG path).

## Build, compilation & tests

### Build
| Command | Params / Notes |
|---|---|
| `build` | `target` (BuildTarget name; default active), `outputPath`, `profileName` (Build Profile, Unity 6 only), `options` (BuildOptions names: Development, AllowDebugging, ConnectWithProfiler, EnableHeadlessMode, SymlinkSources, BuildAdditionalStreamedScenes, CleanBuildCache, DetailedBuildReport), `scenes` (asset paths), `confirm` (req to execute), `dry_run`. Returns `queued` immediately; an editor tick runs the (blocking) build. One build at a time (`busy` otherwise) |
| `build_status` | `idle | queued | building | completed`. On completed: full BuildReport — `buildId`, `result` (Succeeded/Failed/Cancelled/Unknown), `platform`, `outputPath`, `totalSizeBytes`, `buildTimeMs`, `buildStartedAt`/`buildEndedAt` (ISO-8601), `totalWarnings`/`totalErrors`, `files` (path/role/sizeBytes), `packedAssets` (needs DetailedBuildReport), `buildSteps`, `errors`/`warnings`. Reads a Temp status file **off-thread, so polling works while the build holds the main thread**. Report retained until next build |
| `switch_build_target` | `target` (req), `confirm` (req). Destructive + long (full reimport + domain reload). Returns `switching` immediately; `completed` if already on target. Status file survives domain reload |
| `switch_build_target_status` | `idle | switching | completed` (+ success, activeBuildTarget) |
| `list_build_targets` | BuildTargetInfo list (name, displayName, targetGroup, isInstalled), sorted; excludes obsolete/sentinel |
| `get_build_settings` | activeBuildTarget(+Group), developmentBuild, allowDebugging, connectWithProfiler, buildScriptsOnly, symlinkSources, il2CppCodeGeneration, scenes (path/guid/enabled) |
| `set_build_settings` | `settings` (req: developmentBuild, allowDebugging, connectWithProfiler, buildScriptsOnly, symlinkSources, il2CppCodeGeneration=OptimizeSpeed|OptimizeSize), `confirm`, `dry_run`. Does NOT manage scenes or switch target. Returns applied/skipped maps |
| `list_build_profiles` | Unity 6 only; BuildProfileInfo (name, guid, platform, isActive); else code `feature_unavailable` |

### Compilation
| Command | Params / Notes |
|---|---|
| `recompile` | Force script recompile (**works while unfocused/minimized**). Successful compile triggers domain reload (token changes!). Poll below |
| `recompile_status` | `idle | triggered | compiling | completed | up_to_date` |

### Tests
| Command | Params / Notes |
|---|---|
| `list_tests` | `mode` (all/editor/playmode, default all). Returns `TestListResponse` |
| `run_tests` | `mode` (default all), `filter` (case-insensitive partial), `filter_type` (testName/assembly/category, default testName), `include_explicit` (default false), `async_tests` (default false — synchronous by default), `timeout` (default 300 s). Returns `TestExecutionResponse` |
| `test_status` | Status of async run |
| `cancel_tests` | Cancel running execution |

## Project settings

All getters take no params and return `ProjectSettingsResponse`. All setters take `settings` (subset object — omitted fields unchanged), `confirm` (required, refused without), `dry_run`. **Not undoable.**

| Area | Get / Set | Settable fields |
|---|---|---|
| Audio | `get_audio_settings` / `set_audio_settings` | `volume` (0..1), `rolloffScale`, `dopplerFactor` |
| Graphics | `get_graphics_settings` / `set_graphics_settings` | `renderPipelineAsset` (ObjectRef to a RenderPipelineAsset) |
| Input (legacy) | `get_input_settings` / `set_input_settings` | `axis` (req, e.g. `Horizontal`), `sensitivity`, `gravity`, `dead` |
| Physics | `get_physics_settings` / `set_physics_settings` | `gravityX/Y/Z`, `defaultSolverIterations`, `bounceThreshold` |
| Player | `get_player_settings` / `set_player_settings` | `companyName`, `productName`, `bundleVersion`, `scriptingBackend` (Mono2x/IL2CPP — **triggers domain reload**), `apiCompatibilityLevel` (NET_Standard_2_0/NET_Unity_4_8 — **domain reload**); read/written against active build target |
| Quality | `get_quality_settings` / `set_quality_settings` | `level` (index; see levelNames from get), `vSyncCount` (0/1/2), `antiAliasing` (0/2/4/8) |
| Tags & Layers | `get_tags_layers` / `set_tags_layers` | `addTags`[], `removeTags`[], `setLayers`[] of {`index` 8–31 (0–7 reserved), `name` ("" clears slot)} |
| Time | `get_time_settings` / `set_time_settings` | `fixedDeltaTime` (e.g. 0.02), `maximumDeltaTime`, `timeScale` (1 = real-time) |

## Package Manager (UPM)

Registry queries block up to a **25 s timeout**. Add/remove are async by default (`in_progress` → poll `package_status`), `wait:true` blocks. A successful add/remove triggers recompile/domain reload — poll `recompile_status` and expect a **new evalToken**. `busy` if another op is in flight.

| Command | Params / Notes |
|---|---|
| `package_list` | `scope` (installed/available/all, default installed), `include_indirect` (default true), `offline` (default false) |
| `package_search` | `query` (name e.g. com.unity.foo; omit = all), `offline` (default false). Results flag installed state |
| `package_add` | `identifier` (req: `com.unity.foo@1.2.3`, git URL, or `file:../Path`), `confirm` (req), `dry_run`, `wait` (default false) |
| `package_remove` | `name` (req), `confirm` (req), `dry_run`, `wait`. Reload can drop the synchronous reply — `package_status` confirms the outcome |
| `package_resolve` | Fire-and-forget (`Client.Resolve()` on a later tick; response returns before any reload). May trigger recompile/domain reload; outcome recorded in status file |
| `package_status` | `idle | in_progress | completed | failed` + added package, manifest, error. Temp status file **survives domain reload** — recover lost replies by polling. `{"status":"idle"}` if nothing ran |

## Editor lifecycle & observability

| Command | Params / Notes |
|---|---|
| `editor_play` / `editor_stop` / `editor_pause` | Enter / exit / pause Play mode. Return string |
| `editor_status` | Detailed editor state. Returns `StatusResponse` |
| `editor_focus` | Bring the Editor window to foreground |
| `menu` | `path` (e.g. `Assets/Reimport All`; **omit to list all available menu items**). Returns `MenuResponse` |
| `screenshot` | `view` (`game` default, or `scene`), `output` (default timestamped under `/Temp/pipeline-screenshots/`), `width`/`height` (0 = current camera size). Returns `ScreenshotResponse` (file path) |
| `set_autotick` | `enable` (default true), `interval_ms` (default 16; 0 = every update). Forces `EditorApplication.SignalTick` while unfocused. **Static state, resets/off after domain reload** |
| `get_console_logs` | `severity` (all/log/warning/error, default all), `limit` (default 100, cap 1000, most-recent first). Structured |
| `clear_console` | Clears captured buffer + Unity console |
| `get_performance_stats` | Render, memory, frame-timing stats (read-only). Returns `PerformanceStats` |
| `get_authoring_root` / `set_authoring_root` | Get/set base folder under `Assets/` for bare authoring paths (`root` req; use `Assets` for full project access) |

## Runtime / player commands (+ eval & hot reload)

`RuntimeOnly` = only listed on the runtime (Player) server unless noted.

| Command | Params / Notes |
|---|---|
| `runtime_status` | Comprehensive app status. RuntimeOnly. Returns `RuntimeStatusResponse` |
| `quit` | `exitCode` (default 0). Graceful quit. RuntimeOnly |
| `set_target_framerate` | `frameRate` (req; -1 platform default, 0 unlimited). RuntimeOnly |
| `set_timescale` | `scale` (req; 0.0 pause, 1.0 normal). RuntimeOnly |
| `simulate_key` | `key` (req, Input System Key name e.g. Space, W, Enter), `action` (down/up/press, default press). RuntimeOnly; requires Input System (`ENABLE_INPUT_SYSTEM`). Note: only drives the new Input System — games on legacy `Input` will not receive simulated events |
| `simulate_pointer` | `x`, `y` (req, screen px, origin bottom-left), `action` (move/down/up/click, default click), `button` (left/right/middle). RuntimeOnly; Input System required |
| `log` | `message` (req), `level` (info/warning/error). Write to Unity console. RuntimeOnly |
| `console` | `tail` (default 100), `level` (min severity log/warn/error, default log), `since` (cursor, default -1 — follow mode). **Editor AND player.** Returns `ConsoleLogResponse` |
| `eval` | `code` (req, C# via Roslyn), `timeout` (default 5000 ms). **Editor AND runtime.** Returns `EvalResponse` |
| `eval_file` | `file` (req, `.cs` path), `timeout` (default 5000). Missing file / wrong extension / empty → Bad Request |
| `reload_file` | `filename` (req), `timeout` (default 30000), `assemblyDir`, `pdb` (default false). In-place `[HotReload]` edits — see extending.md |
| `reload_file_override` | `filename` (req), `timeout`, `assemblyDir`. `[HotReloadWithOverrides]` flavor |
| `hotreload_status` | Registry stats. RuntimeOnly |
| `cleanup_hotreload` | `assemblyDir` (req), `force_domain_reload` (default true). RuntimeOnly |
