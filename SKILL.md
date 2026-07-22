---
name: unity-cli-editor
description: Control a running Unity Editor (or development Player) from the CLI via the com.unity.pipeline HTTP API — run commands to edit scenes/assets/prefabs, enter play mode, take screenshots, read console logs, recompile, run tests, build, eval C#, and hot-reload code. Use whenever the user wants to drive, inspect, or automate the Unity Editor from Claude Code.
---

# Unity CLI (com.unity.pipeline) — drive the Unity Editor over HTTP

The **`com.unity.pipeline`** package (v0.3.x, experimental) runs a local HTTP server inside the Unity Editor (and optionally inside development Player builds). Clients — the `unity` CLI, CI, or this agent — execute registered commands against it. This is how you can *actually* compile, test, screenshot, and edit scenes without a human in the Editor.

## Prerequisite: package installed?

Check `Packages/manifest.json` for `"com.unity.pipeline"`. If missing, add it (Package Manager → Add by name `com.unity.pipeline`, or add `"com.unity.pipeline": "0.3.1-exp.1"` to the manifest). The Editor must be **running with the project open** for the server to exist.

## Connecting (do this first, every session)

1. **Read the port descriptor** the Editor writes:
   - Editor: `<projectPath>/Library/Pipeline/.unity-pipeline-port`
   - Player: `<workingDirectory>/.unity-pipeline-runtime-port`
2. It's JSON — extract `port` and `evalToken` (also has `pid`, `projectName`, `unityVersion`, `mode`, `lastHeartbeat`).
3. Call `http://127.0.0.1:<port>/...` with header `Authorization: Bearer <evalToken>`. Always use `127.0.0.1`, not `localhost` (IPv6 pitfalls). Missing/wrong token → `401`.

Ports: Editor 7800–7849 (tests 7850–7899), Runtime 7900–7949 (tests 7950–7999). Token is 256-bit CSPRNG, base64, **regenerated after every domain reload** — re-read the descriptor after any recompile/package change.

### Endpoints

| Endpoint | Use |
|---|---|
| `GET /api/status`, `/api/editor_status` | Liveness / editor state |
| `GET /api/commands` | List every registered command (self-documenting — use this to discover) |
| `POST /api/exec` | Run a command: `{"command":"<name>","parameters":{...}}` — the key is `parameters`, NOT `params` (verified; wrong key silently binds nothing) |
| `GET /api/test-status` | Async test status |

### PowerShell recipe (Windows)

```powershell
$d = Get-Content "Library/Pipeline/.unity-pipeline-port" | ConvertFrom-Json
$h = @{ Authorization = "Bearer $($d.evalToken)" }
Invoke-RestMethod -Uri "http://127.0.0.1:$($d.port)/api/exec" -Method Post -Headers $h `
  -ContentType 'application/json' `
  -Body (@{ command = 'editor_status'; parameters = @{} } | ConvertTo-Json -Depth 10)
```

### The `unity` CLI (if installed)

```
unity command <name> [--arg value ...]              # editor of current project
unity command --project-path <path> <name> ...      # explicit project
unity command --runtime MyGame.exe runtime_status   # attach to a dev Player
unity command --runtime-path "C:\Builds\MyGame" runtime_status
```

## Response envelope

Every command returns a `CommandExecutionResponse`: `{ success: bool, command: string, result: <payload>, executionTimeMs: long?, error: string? }`. Authoring commands put an `AuthoringResult` in `result` — assets get `assetPath`/`guid`/`fileId`/`type`/`globalId`; scene objects get `instanceId`/`hierarchyPath`/`type`/`globalId`. **Chain those identities into the next command's `ObjectRef` args.**

## ObjectRef — how you point at things

Any param typed as a reference accepts ONE of: `{"globalId": "..."}`, `{"path": "Assets/Foo.mat"}`, `{"guid": "...", "fileId": ...}`, `{"instanceId": 12345}`, `{"hierarchyPath": "/Root/Child"}`.

## Safety conventions (uniform across all mutating commands)

- `dry_run: true` → validate + preview, mutate **nothing** (wins even if `confirm` is also true).
- `confirm: false` (default) on destructive/overwriting commands → command **refuses**; pass `confirm: true` to apply.
- Scene/GameObject mutations are **Undo-able** (grouped as one Ctrl+Z step). **AssetDatabase writes, file writes, package ops, and settings are NOT undoable.**
- Bare paths (`Materials/Stone`) resolve under the **authoring root** (default `Assets`; read/change via `get_authoring_root` / `set_authoring_root`). `..` traversal is rejected. Explicit `Assets/...` paths work as-is.
- Most scene/asset authoring commands are **blocked during Play mode**.

## Async pattern (fire → poll)

Long operations return immediately; poll their status command until `completed`:

| Start | Poll |
|---|---|
| `build` | `build_status` |
| `switch_build_target` | `switch_build_target_status` |
| `recompile` | `recompile_status` (idle/triggered/compiling/completed/up_to_date) |
| `run_tests` (`async_tests:true`) | `test_status` |
| `package_add` / `package_remove` / `package_resolve` | `package_status` (survives domain reload) |
| `bake_lighting` / `bake_navmesh` / `bake_occlusion_culling` | `lighting_bake_status` / `navmesh_bake_status` / `occlusion_bake_status` |

A domain reload (recompile, package add/remove, scripting-backend change) can drop the in-flight HTTP reply — treat a dropped connection as "poll the status command with a fresh token".

If the Editor is unfocused/minimized it may stop ticking — call `set_autotick` (`enable:true`) first; it auto-disables after a domain reload.

## Common recipes

- **Verify a code change compiles:** `recompile` → poll `recompile_status` → `get_console_logs --severity error`.
- **Run play-mode smoke test:** `editor_play` → `get_console_logs` / `screenshot --view game` → `editor_stop`.
- **Run the test suite:** `run_tests --mode editor --filter <name>` (or `async_tests:true` + poll `test_status`).
- **See what the scene looks like:** `screenshot` (game/scene view) or `capture_game_view` (returns base64 PNG, params width/height/camera/save_path).
- **Inspect a scene:** `get_scene_hierarchy` → nodes carry `instanceId`+`hierarchyPath` → feed into `get_component_properties` / `set_component_properties`.
- **Escape hatch:** `eval --code "<C#>"` runs arbitrary C# via Roslyn (5s default timeout); `eval_file` for a `.cs` file; `menu --path "Assets/Reimport All"` runs any menu item (omit path to list all).

## Field-tested gotchas (verified on this project, 2026-07)

- **`/api/exec` body key is `parameters`, not `params`.** The wrong key doesn't error on commands whose args are all optional — it silently binds nothing. If a command behaves like you passed no args, check this first.
- **Entering play mode rotates the evalToken** (domain reload). Never reuse a token read before `editor_play` — split scripts at every play/recompile/package boundary and re-read the descriptor after.
- **`get_console_logs` can return `total: 0` even when the game is running.** Don't treat an empty result as "no errors" — cross-check by tailing `%LOCALAPPDATA%\Unity\Editor\Editor.log`.
- **`eval` is the best truth source for runtime state.** `list_open_scenes` reflects the edit-mode setup; in play mode query `SceneManager` via `eval` instead.
- Interpolated strings inside `eval` code work fine; return a single string built with `StringBuilder` for multi-part dumps.

## Full reference (read as needed)

- **[references/commands-content.md](references/commands-content.md)** — assets & files, scenes, GameObjects & components, prefabs, scripts, animation/animator/timeline, materials & shaders (every command + every parameter).
- **[references/commands-editor.md](references/commands-editor.md)** — baking (lighting/navmesh/occlusion), search & selection, capture, build/compile/tests, project settings, package manager, editor lifecycle & observability, runtime/player commands, hot reload.
- **[references/connectivity-and-setup.md](references/connectivity-and-setup.md)** — descriptors, ports, auth, runtime (Player) server setup, log file locations.
- **[references/extending.md](references/extending.md)** — writing your own `[CliCommand]`s, the authoring contract (ProjectPaths/ObjectResolver/AuthoringUndoScope), safety conventions, hot-reload authoring (`[HotReload]`/`[HotReloadWithOverrides]`), test architecture.

