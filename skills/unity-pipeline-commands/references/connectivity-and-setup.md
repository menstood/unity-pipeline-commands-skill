# Connectivity & setup (com.unity.pipeline 0.9.x)

## CLI invocation forms

```
unity command                                              # list command groups
unity command <group>                                      # list one group's commands
unity command "<group> <name>" [--arg value ...]           # editor of the current project
unity command --project-path /path/to/project "<group> <name>"
unity command --runtime MyGame.exe "runtime status"        # dev Player by process name
unity command --runtime-path "C:\Builds\MyGame" "runtime status"   # macOS: the .app bundle path
```

With CLI 1.0.0-beta.2, quote the full name: the CLI sends only its first word as the command. `--runtime` / `--runtime-path` go **after** `command` and **before** the command name.

## Discovery: port descriptor files

| Server | Descriptor |
|---|---|
| Editor | `<projectPath>/Library/Pipeline/.unity-pipeline-port` |
| Runtime (Player) | next to the Player: `{Application.dataPath}/..`. On Windows/Linux that's beside the .exe, on macOS the `.app` bundle root, and on Android `persistentDataPath` |

Editor descriptor:

```json
{
  "pid": 12345,
  "port": 7800,
  "projectPath": "/path/to/Project",
  "projectName": "Project",
  "unityVersion": "6000.x.y",
  "mode": "editor",
  "startedAt": "2026-06-25T10:00:00Z",
  "lastHeartbeat": "2026-06-25T10:05:00Z",
  "evalToken": "<base64 token>",
  "capabilities": ["exec.argv", "exec.commandLine", "exec.commandTimeouts", "commands.obsoleteNames"],
  "info": "This editor has not been opened in automated mode and therefore could get stuck on modal dialogs. ...",
  "role": "main",
  "instanceName": "Main Editor",
  "endpoints": [{ "type": "http", "port": "7800" }]
}
```

- `mode` is `editor` or `batchmode`. `port` is the first `http` endpoint, kept for older clients.
- `info` is guidance the client should read before issuing commands. Currently it only warns that an interactive Editor can be blocked by modal dialogs.
- `capabilities`: if the key is absent, the server predates it and supports none of them.
- The Runtime descriptor shares `pid`, `port`, `unityVersion`, `startedAt`, `lastHeartbeat`, `evalToken`, `endpoints`, `capabilities`, and adds `platform`, `buildGuid`, `workingDirectory`.
- **Lifecycle:** the file is written when the server starts, refreshed every 15 s (`lastHeartbeat`), **deleted before every domain reload** and on quit, then rewritten. Tolerate it being briefly missing. A heartbeat older than 60 s means the instance is gone.

## Ports

| Server | Production | Test |
|---|---|---|
| Editor | 7800–7849 | 7850–7899 |
| Runtime | 7900–7949 | 7950–7999 |

Test servers write no descriptor.

## Network & auth

- The server binds the **IPv4 loopback literal only** (`http://127.0.0.1:<port>/`). `Host: localhost` is answered `400`, so always dial `127.0.0.1`. Requests from non-loopback addresses are rejected before auth.
- Requests with an `Origin` header are **rejected**, which blocks browsers. The exception is the opt-in "Allow Browser Clients" setting for sandboxed frames.
- Every request needs `Authorization: Bearer <evalToken>`; missing or wrong gives `401`.
- The token is 256-bit CSPRNG, base64, kept in `SessionState`. It **survives domain reloads and entering play mode**, and is regenerated only on Editor restart or explicit rotation. The descriptor republishes the live token every heartbeat. (In 0.3 it rotated on every reload.) Player builds use a per-process token.

## Endpoints

| Endpoint | Notes |
|---|---|
| `GET /api/status` | `ready`, `settling` (cold import), or `blocked_by_dialog` (with a `dialog` payload). In play mode it also reports `frameCount`, `playerLoopTicking` and `runInBackground` |
| `GET /api/editor_status` | Compiling, domain reload, play mode |
| `GET /api/dialog` | `{active, dialogs:[{id, source, title, message, level, buttons, ...}]}` |
| `GET /api/commands` | `detail=full` (default) / `compact` / `groups` / `tags` / `obsolete_names`; filters `group=`, `tag=`, `query=`, `include_tests=true`; `limit=`/`offset=` paging |
| `POST /api/exec` | Run a command (forms below) |
| `GET /api/job?id=` · `POST /api/job/cancel` `{"id"}` | Detached jobs |
| `GET /api/progress` | Live progress of the running command; answers even while the main thread is blocked |
| `GET /api/test-status` | Async test run status |

## `POST /api/exec` request forms

Each request uses exactly one of these:

```jsonc
{"command": "script.methodreload reload", "parameters": {"filename": "Assets/A.cs"}}   // structured, full name
{"commandLine": "script.methodreload reload Assets/A.cs"}                          // server tokenizes
{"argv": ["script", "eval", "return 2+2;"]}                                        // server binds tokens
```

- **Structured:** `command` is `"<group> <name>"`. A group is one token, dots included (`animation.animator add_state`). The key is `parameters`. With `params`, optional args are silently ignored and only missing required args error.
- **Raw forms:** `argv` is preferred when you already have tokens. `commandLine` uses the pipeline's own tokenizer: `"…"` with `\` escapes, `'…'` literal, no `$VAR`/globbing. Sending `parameters` alongside a raw form is rejected.
- **Name resolution:** first `group name`; then a `global` command; then `group.name`; then a name that's unique across all groups. Old names fail with a rename hint.
- **Optional top-level fields:**
  - `"timeout"` (ms; it overrides the command's own `timeout` parameter, which is in seconds). The default is 60 s.
  - `"job": true` makes it a detached job.
  - `"verbose": true` returns the full envelope with `command`, `executedAt` and `executionTimeMs`.
  - `"omitNulls": true` drops nulls inside `result`.
- **Replies:** lean `{"success", "result"}` by default.
  - Argument errors return `errorCode: "INVALID_COMMAND_ARGS"` with an accumulated `argProblems` list and the command's schema. Nothing ran.
  - `504` + `TIMEOUT` means the request ran out of time, but the command may still be running.
  - `429` means more than 100 requests are queued. Commands run strictly one at a time.

## Readiness

`/api/exec` answers **503** with `"status": "busy"`, `"retryable": true` and a `busyReason`:
- `settling`: right after a cold project import, until the Editor is first idle. This happens once per Editor session.
- `blocked_by_dialog`: a native or `EditorWindow` modal dialog is open (`dialogs` is attached). OS file pickers aren't detected, so fall back to a timeout.

`editor status` and background commands (`console get`, `script recompile_status`, `package status`) still answer while busy.

## Detached jobs

1. `POST /api/exec` `{"command": "...", "parameters": {...}, "job": true}` → `{"success": true, "result": {"jobId": "...", "state": "queued"}}`
2. `GET /api/job?id=<jobId>` → `state`: `queued` | `running` | `completed` | `failed` | `canceled`, plus `progress`, `result`, `error`. Results are kept for the last 100 jobs, for 1 hour.
3. `POST /api/job/cancel` `{"id": "<jobId>"}`. A running job gets a cooperative cancel flag (`PipelineCancellation.ThrowIfCancellationRequested()` in command or eval code).

Jobs have no timeout but **don't survive a domain reload**.

## Connection flow

1. Read the descriptor → `port`, `evalToken`, and `info`.
2. `GET /api/status` until `ready`.
3. Send requests to `http://127.0.0.1:<port>/...` with the bearer header.
4. On connection refused during a reload: wait for the descriptor to reappear (port and token normally persist). On `401`: re-read the descriptor (the Editor restarted or the token was rotated).

## Runtime (Player) server setup

Configured in **Project Settings → Pipeline → Runtime**. No component is needed in any scene: `RuntimePipelineBootstrap` creates the driver at boot.

| Toggle | Applies to | Define |
|---|---|---|
| Enable in Development & Profiled Builds | development / profiled builds (and Play Mode) | `ENABLE_RUNTIME_PIPELINE_DEV` |
| Enable in Release Builds | every other build | `ENABLE_RUNTIME_PIPELINE` |

A build whose toggle is off contains no pipeline code. **Never enable release builds without an explicit request:** that ships a local HTTP server with code execution. Flipping a toggle recompiles the project.

Settings are stored in `ProjectSettings/Packages/com.unity.pipeline/RuntimePipelineConfig.json`:

| Field | Default | Meaning |
|---|---|---|
| `autoStart` | true | Start the server when the Player boots; otherwise call `RuntimePipelineBootstrap.Instance.StartServer()` / `StopServer()` |
| `port` | 0 | 0 = first free port in 7900–7949 |
| `enableAuditLogging` | true | Log remote requests |
| `maxWorkItemsPerFrame` | 10 | Dispatcher work items per frame |

Steps: tick *Enable in Development & Profiled Builds* → File → Build Settings → **Development Build** → build and run. The Player writes `.unity-pipeline-runtime-port` with its port and token.

Builds create transient `Assets/Settings/Pipeline/Resources/RuntimePipelineConfig.asset` and `RuntimePipelineBuildInfo.asset`, which are deleted after the build. Git-ignore them; delete them if an interrupted build leaves them behind.

## Log file locations

| Log | Windows | macOS |
|---|---|---|
| Editor.log | `C:\Users\<user>\AppData\Local\Unity\Editor\Editor.log` | `~/Library/Logs/Unity/Editor.log` |
| Player.log | `C:\Users\<user>\AppData\LocalLow\<company>\<product>\Player.log` | `~/Library/Logs/<company>/<product>/Player.log` |

`Editor.log` also shows when the server starts (`Pipeline: Descriptor written to ...`) and any unhandled server errors. For live logs prefer `console get` (`--level error|warning|log`, `--tail`, `--since` cursor).
