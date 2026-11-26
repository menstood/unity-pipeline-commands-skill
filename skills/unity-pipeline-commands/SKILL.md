---
name: unity-pipeline-commands
description: Control a running Unity Editor (or development Player) via the com.unity.pipeline HTTP API and the unity CLI — edit scenes/assets/prefabs, enter play mode, take screenshots, read console logs, recompile, run tests, build, eval C#, reload methods live. Use when the task requires interacting with a live Unity Editor or Player; NOT for general Unity coding questions that don't need a running Editor.
---

# Unity Pipeline Commands (com.unity.pipeline) — drive the Unity Editor over HTTP

The **`com.unity.pipeline`** package (experimental; this skill targets **0.9.x**, verified on 0.9.1-exp.1) runs a local HTTP server inside the Unity Editor (and optionally inside Player builds). Clients — the `unity` CLI, CI, or this agent — execute registered commands against it. This is how you can *actually* compile, test, screenshot, and edit scenes without a human in the Editor.

**0.9 renamed every command** to `<group> <name>` (`editor_status` → `editor status`, `set_autotick` → `editor set_auto_tick`, `eval` → `script eval`). Old names fail with a hint naming the new one: follow it. Older notes or scripts written for 0.3 need updating.

## Prerequisite: package installed?

Check `Packages/manifest.json` for `"com.unity.pipeline"`. If missing, **report it and ask before installing**. Installing edits the manifest and triggers a recompile plus a domain reload. Once approved, use `unity pipeline install` (with the CLI), or Package Manager → *Install package by name* → `com.unity.pipeline` with the version left blank to get the latest. The Editor must be **running with the project open** for the server to exist.

An Editor in the background may not notice the manifest change until it gets focus. If `unity pipeline list` still shows the server unreachable after a minute and `Editor.log` shows no package resolve, ask the user to click into the Editor once (or press Ctrl+R).

## Connecting (do this first, every session)

### The `unity` CLI — prefer it when installed

Run `unity --version` at session start (verified with **1.0.0-beta.2**; it's a beta and behavior shifts, so `unity --help` is the source of truth). The CLI handles port and token discovery itself.

```
unity pipeline list                          # projects, pipeline version, port, reachability
unity command                                # list command groups
unity command <group>                        # list one group's commands with their parameters
unity command "<group> <name>" --arg value   # run a command
unity command "editor status"
unity command "asset find" --type SceneAsset --name Init
unity command --project-path <path> "editor status"            # explicit project
unity command --runtime MyGame.exe "runtime status"            # attach to a dev Player
unity command --runtime-path "C:\Builds\MyGame" "runtime status"
```

Verified CLI behaviors (1.0.0-beta.2 + pipeline 0.9.1):
- **Quote the full command name.** The CLI sends only the first word as the command, so `unity command editor status` fails with "No command named 'editor'". `unity command "editor status"` works. The package docs show the unquoted form, so newer CLIs may not need quotes. If the unquoted form fails, quote it.
- A name that's unique across groups also works on its own (`unity command eval_file ...` → `script eval_file`). Prefer full names in anything you keep, because a new command can make a bare name ambiguous.
- ObjectRef args take inline JSON. In PowerShell, wrap them in **single quotes with no backslash escapes**: `--target '{"hierarchyPath":"/Foo"}'`. A plain string is treated as a hierarchyPath: `--target '/Foo'`.
- For machine parsing use `--format json --no-banner`. Treat a non-zero exit code as failure and read stderr. (The CLI also echoes its own flags back as `parameters` in the reply; that's harmless.)
- **The CLI stops waiting after about 30 s,** even with `--timeout`, and reports `timed out after 30000ms`. The command keeps running in the Editor. For anything long, use a detached job (below), or have the command write its result to a file under `Temp/` and read that.

### Raw HTTP (when the CLI isn't installed)

1. **Read the descriptor:** `<projectPath>/Library/Pipeline/.unity-pipeline-port` (Player: `<working dir>/.unity-pipeline-runtime-port`). It's JSON with `pid`, `port`, `projectPath`, `projectName`, `unityVersion`, `mode`, `startedAt`, `lastHeartbeat`, `evalToken`, `capabilities`, `endpoints`, `role`, `instanceName`, and sometimes `info`.
2. **Read `info` if present.** For example: "not opened in automated mode … could get stuck on modal dialogs." A modal dialog blocks every main-thread command (see Readiness).
3. Call `http://127.0.0.1:<port>/...` with `Authorization: Bearer <evalToken>`. Always use `127.0.0.1`, not `localhost`. A missing or wrong token gives `401`.

```powershell
$d = Get-Content "Library/Pipeline/.unity-pipeline-port" | ConvertFrom-Json
$h = @{ Authorization = "Bearer $($d.evalToken)" }
Invoke-RestMethod -Uri "http://127.0.0.1:$($d.port)/api/exec" -Method Post -Headers $h `
  -ContentType 'application/json' `
  -Body (@{ command = 'editor status'; parameters = @{} } | ConvertTo-Json -Depth 10)
```

**Token and descriptor lifecycle (0.9):**
- The token **survives domain reloads and entering play mode**. It changes only when the Editor restarts, or on an explicit rotation. (0.3 rotated it on every reload.) On a `401`, re-read the descriptor.
- The descriptor is **deleted just before a domain reload** and rewritten afterwards, so a client must tolerate it briefly missing.
- `lastHeartbeat` refreshes every 15 s. Treat a heartbeat more than 60 s old as a dead Editor.
- **Treat `evalToken` as a secret:** never print, log, or commit it. Descriptors live under `Library/`, which Unity projects git-ignore. Read it only to build the auth header.

### Project identity check (before any mutation)

A reachable server and a valid token do NOT prove you're talking to the right project. Before the first mutating command:
1. Confirm the descriptor's `projectPath` matches the project root you're working in.
2. Confirm `pid` is alive and `lastHeartbeat` is recent.
3. With multiple Editors (or Multiplayer Play Mode clones: check `role` / `instanceName`, and `editor.playmode list_instances`), target explicitly with `--project-path`. Never mutate when identity is ambiguous.

### Endpoints

| Endpoint | Use |
|---|---|
| `GET /api/status` | `ready` / `settling` / `blocked_by_dialog`, plus heartbeat and capabilities |
| `GET /api/editor_status` | Compiling, domain reload, play mode, run-in-background |
| `GET /api/dialog` | Open modal dialog(s) blocking the main thread |
| `GET /api/commands` | Every command with parameters. Query options: `detail=compact\|groups\|tags`, `group=`, `query=`, `limit=` (use `limit=10000` to get all) |
| `POST /api/exec` | Run a command: `{"command":"<group> <name>","parameters":{...}}`. The key is `parameters`, NOT `params` (re-verified on 0.9.1: the wrong key is silently ignored for optional args, and only required args raise an error). Optional top-level fields: `"timeout"` (ms), `"job": true`, `"verbose": true` |
| `GET /api/job?id=` · `POST /api/job/cancel` | Detached job result and cancel |
| `GET /api/progress` | Live progress of the running command (answers even while the main thread is blocked) |
| `GET /api/test-status` | Async test status |

### Readiness: 503 means busy, not broken

`/api/exec` answers **HTTP 503** with `"busyReason": "settling"` while the Editor finishes a cold import, and with `"blocked_by_dialog"` while a modal dialog is open (`GET /api/dialog` shows it). Wait, or ask the user to dismiss the dialog, then retry. `editor status` and background commands (`console get`, `script recompile_status`, `package status`) stay available while busy.

### Long-running commands: detached jobs and server-side waits

- **Detached job:** add `"job": true` to the `/api/exec` body. You get `{"jobId", "state": "queued"}` back immediately; poll `GET /api/job?id=<jobId>` until `state` is `completed` / `failed` / `canceled`. Jobs have no timeout and their results are kept for an hour, but jobs don't survive a domain reload. This is the fix for the CLI's 30 s wait.
- **Request timeout:** a top-level `"timeout"` in ms (the CLI's `--timeout` takes seconds). Defaults: 60 s, `script eval` 30 s, `test run` 600 s. When it runs out you get `504 TIMEOUT`, but the command may still be running.
- **`job wait`:** waits server-side for a condition (optionally acting in the same frame) instead of client polling loops. `"async": true` returns a `waitId` to collect later with `job wait_status`.
- **`job batch`:** runs several commands in one request, transactional (one Undo step) by default. Later operations can reference earlier results (`"$0.instanceId"`). **Batch operations use `params`, not `parameters`.**

## Response envelope

Replies are **lean by default**: `{"success": true, "result": ...}`. On failure you get `success: false` with `error`, `errorDetails`, and possibly `warnings`. `errorCode: "INVALID_COMMAND_ARGS"` (with `argProblems`) means the arguments couldn't be bound and nothing ran. Pass `"verbose": true` to also get `command`, `executedAt`, and `executionTimeMs`.

Authoring commands return an `AuthoringResult`. Assets carry `assetPath` / `guid` / `fileId` / `type` / `globalId`; scene objects carry `instanceId` / `hierarchyPath` / `type` / `globalId`. **Chain those identities into the next command's `ObjectRef` args.**

## ObjectRef — how you point at things

Any reference parameter accepts ONE of: `{"globalId": "..."}`, `{"path": "Assets/Foo.mat"}`, `{"guid": "...", "fileId": ...}`, `{"instanceId": 12345}`, `{"hierarchyPath": "/Root/Child"}`.

## Safety conventions

`confirm`/`dry_run` are **per-command conventions, not a global guarantee**. Non-destructive commands and custom commands may implement neither. Check the command's parameters (`unity command <group>` or `GET /api/commands?group=<group>`) before relying on them.

- `dry_run: true` → validate and preview, mutate **nothing** (wins even if `confirm` is also true).
- `confirm: false` (the default) on destructive or overwriting commands → the command **refuses**. Pass `confirm: true` to apply.
- Scene/GameObject mutations are **Undo-able** (grouped as one Ctrl+Z step). **AssetDatabase writes, file writes, package operations, and settings are NOT undoable.** If the project has no version control, say so before making such changes.
- Bare paths (`Materials/Stone`) resolve under the **authoring root** (default `Assets`; read or change it with `authoring get_root` / `authoring set_root`). `..` traversal is rejected. Explicit `Assets/...` paths work as-is.
- Most scene and asset authoring commands are **blocked during Play mode**.

## Async pattern (fire → poll)

| Start | Poll |
|---|---|
| `build run` | `build status` |
| `build.target switch` | `build.target switch_status` |
| `script recompile` | `script recompile_status` (idle / triggered / compiling / completed / up_to_date) |
| `test run` (`async_tests: true`) | `test status` |
| `package add` / `package remove` / `package resolve` (or `wait: true`) | `package status` (survives domain reload) |
| `lighting bake` / `navmesh bake` / `occlusion bake` | `lighting bake_status` / `navmesh bake_status` / `occlusion bake_status` |

A domain reload (recompile, package add or remove, scripting-backend change) can drop the in-flight HTTP reply. Treat a dropped connection as "wait for the descriptor to reappear, then poll the status command".

If the Editor is unfocused or minimized it may stop ticking. Call `editor set_auto_tick` (`enable: true`; `persist` defaults to true) first. In Play mode an unfocused Editor also stops the player loop unless `editor.playmode set_run_in_background` is on. `editor status` reports `playerLoopTicking`.

## Common recipes

- **Verify a code change compiles:** `script recompile` → poll `script recompile_status` → `console get --level error`.
- **Play-mode smoke test:** `editor.playmode start` → `console get` / `capture screenshot --view game` → `editor.playmode stop`.
- **Run the test suite:** `test run --mode editor --filter <name>` (or `async_tests: true` + poll `test status`).
- **See what the scene looks like:** `capture screenshot --view scene|game --output <path>`, or `capture scene_view` / `capture game_view` for inline base64. Frame the Scene view first with `SceneView.lastActiveSceneView.LookAt(...)` via `script eval`.
- **Inspect a scene:** `scene get_hierarchy` → nodes carry `instanceId` + `hierarchyPath` → `component get_fields` / `component set_field`.
- **Write a text asset:** `asset write_text --path ... --contents ...` (writes and imports; `confirm: true` to overwrite).
- **Escape hatch:** `script eval --code "<C#>"` runs C# via Roslyn (30 s default timeout). `script eval_file --file <path.cs>` runs a file, and `script run` runs a static entry point of a project file. `editor invoke_menu --path "Assets/Reimport All"` runs any menu item (omit `path` to list them). Policy:
  - Prefer a registered command when one exists.
  - Use eval mainly for read-only inspection.
  - Ask before eval or menu calls that write files, start processes, or touch the network.
  - Verify the effect afterwards.
  - `eval_file` can't take arguments: pass inputs through a small config file under `Temp/`.

## Field-tested gotchas

Re-verified on 0.9.1 (2026-11) unless marked otherwise:

- **`/api/exec` body key is `parameters`, not `params`.** The wrong key silently binds nothing for optional args: `console get` with `params: {tail: 1}` ignored the tail and returned every entry. Only a missing required arg errors. (`job batch` operations are the exception: they use `params`.)
- **Old 0.3 command names fail** with "It was renamed: run 'unity command <group> <name>'". Use the new name.
- **Your own failed commands appear as console errors** (`ExecuteCommandByName: No command named ...`). Run `console clear` before a check so you don't blame the project for them.
- **CLI 30 s wait:** see above. Write long results to `Temp/` files or use detached jobs.
- **First renders compile shader variants** and can block the Editor for a minute or more. Status calls time out meanwhile. Wait for `editor status` to answer again instead of re-sending.
- **Setting a material value right after its shader reimports can be lost.** Verify by reading the `.mat` file back.
- **`Material.SetColor` converts sRGB to linear** in a linear-space project (0.5 → 0.214). Use `Color.linear` when computing expected pixel values.
- *(0.3, not re-tested on 0.9)* **`console get` could return nothing while the game was running.** Don't treat an empty result as "no errors": cross-check `%LOCALAPPDATA%\Unity\Editor\Editor.log`.
- **`script eval` is the best truth source for runtime state.** The scene list reflects the edit-mode setup; in play mode query `SceneManager` through eval. Return one string built with `StringBuilder` for multi-part dumps. Internal Unity APIs (e.g. Shader Graph's importer) are reachable by reflection.

## Full reference (read as needed)

- **[references/commands-content.md](references/commands-content.md)** — authoring commands, generated from the live 0.9.1 schema: assets, scenes, GameObjects and components, prefabs, scripts (eval, run, method reload), animation, materials.
- **[references/commands-editor.md](references/commands-editor.md)** — build, capture, console, diagnostics, editor and play mode, jobs (batch, wait), baking (lighting, navmesh, occlusion), packages, runtime, project settings, tests.
- **[references/connectivity-and-setup.md](references/connectivity-and-setup.md)** — descriptors, ports, auth, raw request forms, readiness, jobs, Player server setup, log locations.
- **[references/extending.md](references/extending.md)** — writing your own commands (`[CliGroupCommand]`), the authoring contract, method reload (`[MethodReload]`), test architecture.
- **`scripts/gen_command_reference.py <project>`** — regenerates the two command references from a running Editor after a package update.
