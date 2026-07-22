# Connectivity & setup

## CLI invocation forms

```
unity command <name> [--arg value ...]                 # editor of the current project
unity command --project-path /path/to/project <name>   # explicit project
unity command --runtime MyGame.exe runtime_status      # dev Player by process name
unity command --runtime-path "C:\Builds\MyGame" runtime_status
```

## Discovery: port descriptor files

- **Editor:** `<projectPath>/Library/Pipeline/.unity-pipeline-port`
- **Runtime (Player):** `<workingDirectory>/.unity-pipeline-runtime-port`

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
  "evalToken": "<base64 token>"
}
```

Runtime descriptor shares `pid`/`port`/`unityVersion`/`startedAt`/`lastHeartbeat`/`evalToken` and adds `platform` (e.g. `WindowsPlayer`), `buildGuid`, `workingDirectory`.

Use `lastHeartbeat`/`pid` to detect a stale descriptor from a dead Editor.

## Ports

| Server | Production | Test |
|---|---|---|
| Editor | 7800–7849 | 7850–7899 |
| Runtime | 7900–7949 | 7950–7999 |

## Network & auth

- Binds **IPv4 loopback only** (`127.0.0.1`, plus `localhost` hostname for compatibility). Connect to `127.0.0.1` explicitly to avoid IPv6 resolution issues.
- Requests with an `Origin` header are **rejected** (anti-browser attack).
- Every request needs `Authorization: Bearer <evalToken>`; missing/wrong → `401 Unauthorized`.
- Token: `SecurityTokenManager.GetOrCreateToken()` — 256 bits CSPRNG, base64, held in memory, **regenerated after each domain reload** (recompile, package add/remove, play-mode reload with default settings). Always re-read the descriptor after any operation that reloads the domain.

## Endpoints

`GET /api/status` · `GET /api/editor_status` · `GET /api/commands` (list all registered commands with args — the API is self-documenting) · `POST /api/exec` (`{"command": "...", "parameters": {...}}` — key must be `parameters`, not `params`) · `GET /api/test-status`

## Connection flow

1. Read descriptor file → extract `port` + `evalToken`.
2. HTTP to `http://127.0.0.1:<port>/...` with the bearer header.
3. On connection refused / 401 after a reload: re-read the descriptor (port may persist, token won't).

## Runtime (Player) server setup

Server runs in **development builds only**, gated by `#if UNITY_EDITOR || (UNITY_STANDALONE && DEBUG)` — `DEBUG` is defined only for standalone Development Builds, so release builds physically can't run it (it exposes `eval`).

1. Add **RuntimePipelineManager** component (Add Component → Pipeline → Runtime Pipeline Manager) to a startup-scene GameObject. `[DisallowMultipleComponent]`, `DontDestroyOnLoad`; its `Update()` pumps the server dispatcher.
2. Inspector fields:

| Field | Default | Purpose |
|---|---|---|
| `enableInBuilds` | false | Master switch — server only starts when true |
| `autoStart` | true | Start server in `Start()`; else call `StartServer()`/`StopServer()` |
| `port` | 0 | 0 = auto-assign from 7900–7949 |
| `requestTimeoutMs` | 30000 | Per-request timeout |
| `enableAuditLogging` | true | Log remote requests |
| `maxWorkItemsPerFrame` | 10 | Work items per frame |

3. File → Build Settings → enable **Development Build** (Standalone Win/macOS/Linux).
4. Build + run → server binds first free port in 7900–7949 and writes `.unity-pipeline-runtime-port` next to the executable's working directory.

## Log file locations

| Log | Windows | macOS |
|---|---|---|
| Editor.log | `C:\Users\<user>\AppData\Local\Unity\Editor\Editor.log` | `~/Library/Logs/Unity/Editor.log` |
| Player.log | `C:\Users\<user>\AppData\LocalLow\<company>\<product>\Player.log` | `~/Library/Logs/<company>/<product>/Player.log` |

(For live logs prefer the `console` / `get_console_logs` commands over tailing files.)
