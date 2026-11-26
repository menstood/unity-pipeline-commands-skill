# Editor, build, settings, packages, runtime and job commands

Generated from the live command schema (`GET /api/commands`) of `com.unity.pipeline` **0.9.1-exp.1** on Unity 6000.3.13f1: 166 commands. Regenerate with `scripts/gen_command_reference.py` after a package update; `unity command <group>` / `GET /api/commands?group=<group>` is the source of truth for the installed version.

Run as `unity command "<group> <name>" --param value` (quote the full name with CLI 1.0.0-beta.2), or raw `POST /api/exec` `{"command": "<group> <name>", "parameters": {...}}`. **(req)** = required; `=x` = default. ObjectRef = `{"path"|"guid"+"fileId"|"instanceId"|"hierarchyPath"|"globalId": ...}`. Destructive commands follow the `confirm`/`dry_run` convention (see SKILL.md).

## `build`

| Command | Parameters | Description |
|---|---|---|
| `build create_profile` | `name` string **(req)**, `platform` string **(req)**, `subtarget` string, `folder` string, `activate` bool =false, `confirm` bool =false, `dry_run` bool =false | Create a Build Profile asset for a platform (Unity 6 only). Call build list_platforms first to get a platform id. Returns feature_unavailable on earlier versions. |
| `build get_settings` | — | Read the current build configuration from EditorUserBuildSettings / EditorBuildSettings. |
| `build list_platforms` | `showAll` bool =false | List the platforms a Build Profile can target, with their platform id (Unity 6 only). Lists only platforms whose build support is installed; pass showAll=true for every known platform. |
| `build list_profiles` | — | List Build Profile assets in the project (Unity 6 only). Returns feature_unavailable on earlier versions. |
| `build run` | `target` string, `outputPath` string, `profileName` string, `options` string[], `scenes` string[], `confirm` bool =false, `dry_run` bool =false, `timeout` double =60.0 | Trigger an async Player build and report the full BuildReport. Returns immediately (queued); poll build status until status is 'completed'. DetailedBuildReport is included by default unless 'options' is supplied. Use dry_run to validate without building. |
| `build set_profile` | `name` string **(req)**, `folder` string, `overrideGlobalScenes` Nullable`1, `scenes` string[], `scriptingDefines` string[], `confirm` bool =false, `dry_run` bool =false | Edit an existing Build Profile's scene list and scripting defines (Unity 6 only). Every setting is optional; only the ones supplied change. The platform cannot be changed here: recreate the profile with build create_profile and confirm=true. Returns feature_unavailable on earlier versions. |
| `build set_settings` | `settings` SetBuildSettingsInput, `confirm` bool =false, `dry_run` bool =false | Set mutable EditorUserBuildSettings fields. Does NOT manage scenes (use scene add_to_build / scene remove_from_build) or switch target (use build.target switch). Use dry_run to preview. |
| `build status` | — | Status of the current/most recent build: idle \| queued \| building \| completed, with the full BuildReport (files, packedAssets, buildSteps, errors, warnings) once completed. Retained until the next build. |

## `build.target`

| Command | Parameters | Description |
|---|---|---|
| `build.target list` | — | List the known BuildTarget values with their group and whether build support is installed. |
| `build.target switch` | `target` string **(req)**, `confirm` bool =false, `timeout` double =60.0 | Switch the active build target (destructive, long-running: triggers a full reimport + domain reload). Requires confirm=true. Returns immediately; poll build.target switch_status. |
| `build.target switch_status` | — | Status of the last target switch: idle \| switching \| completed (with success + activeBuildTarget). |

## `capture`

| Command | Parameters | Description |
|---|---|---|
| `capture game_view` | `width` int =1280, `height` int =720, `camera` string, `save_path` string, `include_inline_image` bool =false, `max_resolution` int =0, `source` string | Capture the game view as a PNG. source=screen (default) captures what the Game window shows, incl. Screen Space - Overlay UI; source=camera renders a single camera instead and misses overlay UI. Returns it inline as base64, unless save_path is set (path-only result; pass include_inline_image=true to get both). |
| `capture scene_view` | `width` int =1280, `height` int =720, `save_path` string, `include_inline_image` bool =false, `max_resolution` int =0 | Render the active Scene View to a PNG. Returns it inline as base64, unless save_path is set (path-only result; pass include_inline_image=true to get both). |
| `capture screenshot` | `view` string =game, `output` string, `width` int =0, `height` int =0 | Capture the Scene or Game view as a PNG and return its file path |

## `console`

| Command | Parameters | Description |
|---|---|---|
| `console clear` | — | Clear the captured log buffer and the Unity Editor console. |
| `console get` | `tail` int =100, `level` string =log, `since` long =-1, `since_session` string | Get captured Unity console output (Editor or Player; supports tail, level filtering, and follow via a cursor) |
| `console status` | — | Console ground truth and buffer counters without pulling entries: compile-failure flag, Editor console counts, and the buffer's retained counts and cursor. |
| `console write` | `message` string **(req)**, `level` string =info | Write a message to Unity console |

## `diagnostics`

| Command | Parameters | Description |
|---|---|---|
| `diagnostics audit_status` | — | Get the status of the last audit: idle \| scanning \| completed \| failed \| interrupted \| unavailable. |
| `diagnostics get_performance` | — | Read render, memory, and frame-timing stats (structured, read-only). |
| `diagnostics report_evals` | `top` int =50 | Aggregate local eval-usage telemetry into a ranked report: API fingerprint frequency, one-liner percentage, error rate, and command-coverage suggestions. |
| `diagnostics run_audit` | `categories` string, `output` string | Run a Project Auditor static-analysis scan. Returns immediately; poll diagnostics audit_status until status is 'completed', then read the CSV. |

## `editor`

| Command | Parameters | Description |
|---|---|---|
| `editor focus` | — | Bring the Unity Editor window to the foreground |
| `editor invoke_menu` | `path` string | Execute an Editor menu item by path, or list available items when no path is given |
| `editor save_all` | — | Save all open scenes that have unsaved changes. |
| `editor search` | `query` string **(req)**, `limit` int =50 | Run a Unity Search query and return structured results. |
| `editor set_auto_tick` | `enable` bool =true, `interval_ms` int =16, `persist` bool =true | Keep the editor ticking while unfocused by forcing EditorApplication.SignalTick at a throttled rate |
| `editor status` | — | Get detailed Unity Editor status and state information |

## `editor.playmode`

| Command | Parameters | Description |
|---|---|---|
| `editor.playmode list_instances` | — | List running Editor instances reachable over Pipeline (this Editor + its MPPM virtual player clones). Connect to one with 'unity command --project-path <its projectPath>'. |
| `editor.playmode pause` | — | Toggle pause state of Unity Editor play mode |
| `editor.playmode set_run_in_background` | `enable` bool =true | Override the project's Run In Background Player Setting, recording enough state to restore it later and to keep it out of builds |
| `editor.playmode start` | — | Enter Unity Editor play mode |
| `editor.playmode stop` | — | Exit Unity Editor play mode |

## `job`

| Command | Parameters | Description |
|---|---|---|
| `job batch` | `operations` List`1 **(req)**, `transactional` bool =true, `on_error` string =abort, `dry_run` bool =false, `result_fields` JObject, `timeout` double =60.0 | Run multiple registered commands in one transactional request. Later ops can reference earlier results with "$<id-or-index>.<jsonPath>" (e.g. "$0.instanceId"; "$$" escapes a literal '$'). transactional=true (default) groups every op into one Undo step and reverts all applied ops if any op fails; commands that mutate outside the Undo system (asset/file/settings writes) are rejected unless transactional=false. on_error=abort\|continue (continue forces transactional=false); dry_run validates without mutating; timeout (seconds, default 60) bounds execution — when it is about to run out the remaining ops are skipped and a transactional batch rolls back (submit long batches with "job": true). Excludes build run, build.target switch, the package commands, editor.playmode start/stop/pause, script recompile, script eval, script eval_file, script run, editor invoke_menu, scene open/scene create, async commands (test run/test list), runtime-only commands, and nested job batch. |
| `job wait` | `condition` WaitConditionInput **(req)**, `timeout` double =30.0, `poll_interval_ms` double =100.0, `on_met` WaitOnMetInput, `return_history` bool =false, `tolerate_missing` bool =false, `async` bool =false | Wait server-side until a member condition holds, then optionally act in the same frame. Sync waits hold the exec queue (every other command waits behind them, including one the condition may depend on) — keep them short and self-contained; set async=true and poll job wait_status for anything else. |
| `job wait_cancel` | `wait_id` string **(req)** | Cancel an async wait started with job wait (async=true). |
| `job wait_status` | `wait_id` string **(req)** | Get the status/result of an async wait started with job wait (async=true). |

## `lighting`

| Command | Parameters | Description |
|---|---|---|
| `lighting bake` | `confirm` bool =false, `dry_run` bool =false | Trigger an async lightmap bake of the open scene(s) via Lightmapping.BakeAsync(). Returns immediately; poll lighting bake_status until completed. |
| `lighting bake_status` | — | Get the status of the last lighting bake: idle \| baking \| completed. |
| `lighting cancel_bake` | — | Cancel an in-progress lighting bake (Lightmapping.Cancel()). |
| `lighting clear_bake` | `confirm` bool =false, `include_disk_cache` bool =false, `dry_run` bool =false | Clear baked lightmap data for the open scene(s). Destructive: requires confirm=true. |
| `lighting get_settings` | — | Read the active LightingSettings (lightmapper, bounces, resolution, directional mode, AO, etc.). |
| `lighting set_settings` | `settings` JObject **(req)**, `dry_run` bool =false | Apply a subset of lighting settings to the active LightingSettings. Returns { applied[], unknown[] }. |

## `navmesh`

| Command | Parameters | Description |
|---|---|---|
| `navmesh bake` | `confirm` bool =false, `dry_run` bool =false | Trigger an async legacy NavMesh bake of the open scene(s) via UnityEditor.AI.NavMeshBuilder. Returns immediately; poll navmesh bake_status until completed. |
| `navmesh bake_status` | — | Get the status of the last NavMesh bake: idle \| baking \| completed. |
| `navmesh bake_surfaces` | — | Bake NavMeshSurface components (AI Navigation package). v1 stub: returns package_not_found when the package is absent. |
| `navmesh cancel_bake` | — | Cancel an in-progress NavMesh bake (NavMeshBuilder.Cancel()). |
| `navmesh clear_bake` | `confirm` bool =false, `dry_run` bool =false | Clear the baked NavMesh for the open scene(s). Destructive: requires confirm=true. |
| `navmesh get_settings` | — | Read the default agent's legacy NavMesh bake settings (agentRadius/Height/Slope/Climb, minRegionArea, voxelSize). |
| `navmesh set_settings` | `settings` JObject **(req)**, `dry_run` bool =false | Apply a subset of legacy NavMesh bake settings to the default agent. Returns { applied[], unknown[] }. |

## `occlusion`

| Command | Parameters | Description |
|---|---|---|
| `occlusion bake` | `smallest_occluder` float =-3.40282347e+38, `smallest_hole` float =-3.40282347e+38, `backface_threshold` float =-3.40282347e+38, `confirm` bool =false, `dry_run` bool =false | Trigger an async occlusion-culling bake of the open scene(s) via StaticOcclusionCulling.GenerateInBackground(). Returns immediately; poll occlusion bake_status until completed. |
| `occlusion bake_status` | — | Get the status of the last occlusion bake: idle \| baking \| completed. |
| `occlusion cancel_bake` | — | Cancel an in-progress occlusion bake (StaticOcclusionCulling.Cancel()). |
| `occlusion clear_bake` | `confirm` bool =false, `dry_run` bool =false | Clear baked occlusion-culling data for the open scene(s). Destructive: requires confirm=true. |

## `package`

| Command | Parameters | Description |
|---|---|---|
| `package add` | `identifier` string **(req)**, `confirm` bool =false, `dry_run` bool =false, `wait` bool =false, `timeout` double =300.0 | Add a UPM package by name@version, git URL, or 'file:' local path. Async by default (returns in_progress; poll package status); pass wait=true to block until added. A recompile/domain reload follows — poll script recompile_status. Requires confirm=true; use dry_run to preview. |
| `package list` | `scope` string =installed, `include_indirect` bool =true, `offline` bool =false, `timeout` double =60.0 | List packages by scope: installed (default) \| available (registry) \| all (both). Returns the full result synchronously — available/all block until the registry query completes. |
| `package remove` | `name` string **(req)**, `confirm` bool =false, `dry_run` bool =false, `wait` bool =false, `timeout` double =300.0 | Remove a UPM package by name. Async by default (returns in_progress; poll package status); pass wait=true to block until removed. A recompile/domain reload follows — poll script recompile_status. Requires confirm=true; use dry_run to preview. |
| `package resolve` | — | Resolve/refresh packages from the manifest (re-fetch and re-link). May trigger a recompile/domain reload — poll script recompile_status. Its outcome is recorded for package status. |
| `package search` | `query` string, `offline` bool =false, `timeout` double =60.0 | Search packages available in the registry. Provide a name (e.g. com.unity.foo) or omit to list all. Returns the full result synchronously (blocks until the registry query completes). |
| `package status` | — | Status of the last async package operation (add/remove/resolve): idle \| in_progress \| completed \| failed, with the added package, manifest, and any error. |

## `runtime`

| Command | Parameters | Description |
|---|---|---|
| `runtime quit` | `exitCode` int =0 | Gracefully quit the Unity application |
| `runtime set_target_frame_rate` | `frameRate` int **(req)** | Set the target frame rate for the application |
| `runtime set_time_scale` | `scale` float **(req)** | Set the time scale for the application |
| `runtime simulate_key` | `key` string **(req)**, `action` string =press | Simulate a keyboard key event (Input System). Drives the running app. |
| `runtime simulate_pointer` | `x` float **(req)**, `y` float **(req)**, `action` string =click, `button` string =left | Simulate a mouse/pointer event at screen coordinates (Input System). |
| `runtime status` | — | Get comprehensive runtime application status |

## `settings.audio`

| Command | Parameters | Description |
|---|---|---|
| `settings.audio get` | — | Read project Audio settings (volume, rolloff scale, doppler factor). |
| `settings.audio set` | `settings` AudioSettingsInput, `confirm` bool =false, `dry_run` bool =false | Change project Audio settings. Requires confirm=true; use dry_run to preview. Not undoable via Ctrl+Z. |

## `settings.graphics`

| Command | Parameters | Description |
|---|---|---|
| `settings.graphics get` | — | Read GraphicsSettings (default render pipeline). |
| `settings.graphics set` | `settings` GraphicsSettingsInput, `confirm` bool =false, `dry_run` bool =false | Set the default render pipeline asset. Requires confirm=true; use dry_run to preview. Not undoable via Ctrl+Z. |

## `settings.input`

| Command | Parameters | Description |
|---|---|---|
| `settings.input get` | — | Read the legacy Input Manager axes (names and count). |
| `settings.input set` | `settings` InputAxisInput, `confirm` bool =false, `dry_run` bool =false | Tune a legacy Input Manager axis (sensitivity/gravity/dead) by name. Requires confirm=true; use dry_run to preview. Not undoable via Ctrl+Z. |

## `settings.physics`

| Command | Parameters | Description |
|---|---|---|
| `settings.physics get` | — | Read Physics settings (gravity, solver iterations, bounce threshold). |
| `settings.physics set` | `settings` PhysicsSettingsInput, `confirm` bool =false, `dry_run` bool =false | Change Physics settings. Requires confirm=true; use dry_run to preview. Not undoable via Ctrl+Z. |

## `settings.player`

| Command | Parameters | Description |
|---|---|---|
| `settings.player get` | — | Read PlayerSettings (company/product/version, scripting backend, API level). |
| `settings.player set` | `settings` PlayerSettingsInput, `confirm` bool =false, `dry_run` bool =false | Change PlayerSettings. Requires confirm=true; use dry_run to preview. Not undoable via Ctrl+Z. Scripting backend / API level changes trigger a domain reload. |

## `settings.quality`

| Command | Parameters | Description |
|---|---|---|
| `settings.quality get` | — | Read QualitySettings (current level, level names, vSync, anti-aliasing). |
| `settings.quality set` | `settings` QualitySettingsInput, `confirm` bool =false, `dry_run` bool =false | Change QualitySettings. Requires confirm=true; use dry_run to preview. Not undoable via Ctrl+Z. |

## `settings.runtime_pipeline`

| Command | Parameters | Description |
|---|---|---|
| `settings.runtime_pipeline get` | — | Read Pipeline Runtime settings (enableInDevelopmentBuilds, enableInReleaseBuilds, port, enableAuditLogging, autoStart, maxWorkItemsPerFrame). Reports the settings in effect, falling back to built-in defaults when none have been authored; never creates the settings file. The two toggles are reported for the active build target. |
| `settings.runtime_pipeline set` | `settings` RuntimePipelineSettingsInput, `confirm` bool =false, `dry_run` bool =false | Change Pipeline Runtime settings. Requires confirm=true; use dry_run to preview. Not undoable via Ctrl+Z. Refused while in Play Mode: the running driver already loaded its own settings, so a change would silently not apply until the next Play session or build. port and maxWorkItemsPerFrame are rejected outright if outside the same bounds the Project Settings page enforces. |

## `settings.tags_layers`

| Command | Parameters | Description |
|---|---|---|
| `settings.tags_layers get` | — | Read the project's tags and (named) layers. |
| `settings.tags_layers set` | `settings` TagsLayersInput, `confirm` bool =false, `dry_run` bool =false | Add/remove tags and assign user layer names (index 8-31). Requires confirm=true; use dry_run to preview. Not undoable via Ctrl+Z. |

## `settings.time`

| Command | Parameters | Description |
|---|---|---|
| `settings.time get` | — | Read Time settings (fixedDeltaTime, maximumDeltaTime, timeScale). |
| `settings.time set` | `settings` TimeSettingsInput, `confirm` bool =false, `dry_run` bool =false | Change Time settings. Requires confirm=true; use dry_run to preview. Not undoable via Ctrl+Z. |

## `test`

| Command | Parameters | Description |
|---|---|---|
| `test cancel` | — | Cancel running test execution |
| `test list` | `mode` string =all | List all available tests (EditMode and/or PlayMode) without running them |
| `test run` | `mode` string =all, `filter` string, `filter_type` string =testName, `include_explicit` bool =false, `async_tests` bool =false, `timeout` double =600.0 | Execute Unity tests with filtering options |
| `test status` | — | Get status of running async test execution |
