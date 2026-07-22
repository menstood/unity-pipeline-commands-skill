# unity-pipeline-commands-skill

Skill and command reference for controlling a running Unity Editor (or development Player) through the local HTTP API of the experimental [`com.unity.pipeline`](https://docs.unity3d.com/Packages/com.unity.pipeline@latest) package: scene/asset/prefab authoring, play mode, screenshots, console logs, recompile, tests, builds, project settings, packages, C# eval, hot reload.

Written for Claude Code (`SKILL.md` format), usable by any agent framework or human that reads markdown. `references/` doubles as a standalone API reference for the package, distilled from the full [`com.unity.pipeline@0.3` manual](https://docs.unity3d.com/Packages/com.unity.pipeline@0.3/manual/index.html) and corrected against a live Editor.

## Requirements

- Unity 6.0+, project open in a running Editor
- `com.unity.pipeline` package installed in the project (below)
- Optional: [Unity CLI](https://docs.unity.com/en-us/unity-cli) — preferred client when present; otherwise the HTTP API is called directly

## Installation

### Skill

Per project:

```bash
git clone https://github.com/menstood/unity-pipeline-commands-skill.git .claude/skills/unity-pipeline-commands
```

Global (all projects):

```bash
git clone https://github.com/menstood/unity-pipeline-commands-skill.git ~/.claude/skills/unity-pipeline-commands
```

For non-Claude tooling, clone anywhere and point your agent at `SKILL.md`.

### `com.unity.pipeline` package

Without the Unity CLI: **Window → Package Manager → + → Install package by name** → `com.unity.pipeline` (leave version blank to get the latest).

With the Unity CLI, from the project folder while the project is open:

```bash
unity auth login
unity pipeline install
unity pipeline list        # verify: "Pipeline: Installed"
```

### Unity CLI (optional)

```bash
# macOS / Linux (Windows: bash-capable shell, e.g. Git Bash)
curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash
```

Reopen terminal; verify with `unity --version`. Update with `unity upgrade`.

## Usage

- Claude Code: `/unity-pipeline-commands`, or any request that touches the Editor.
- Unity CLI: `unity command` lists all commands; `unity command <name> [--arg value ...]` executes.
- Raw HTTP: read `<project>/Library/Pipeline/.unity-pipeline-port` for port + token, then `POST http://127.0.0.1:<port>/api/exec` with `Authorization: Bearer <token>` and body `{"command":"<name>","parameters":{...}}`. Full recipe in `SKILL.md`.

## Contents

| File | Contents |
|---|---|
| `SKILL.md` | Connection (CLI + raw HTTP), auth/token semantics, safety conventions (`confirm`/`dry_run`), async fire-and-poll patterns, common workflows, field-tested gotchas |
| `references/commands-content.md` | Authoring commands: assets & files, scenes, GameObjects & components, prefabs, scripts, animation, materials & shaders |
| `references/commands-editor.md` | Baking, search & selection, capture, build/compile/tests, project settings, package manager, editor lifecycle & observability, runtime commands, hot reload |
| `references/connectivity-and-setup.md` | Port descriptors, port ranges, token rotation, endpoints, dev-Player server setup, log locations |
| `references/extending.md` | Custom `[CliCommand]` authoring, authoring contract, hot-reload authoring, test architecture |

## Tested with

| Component | Version |
|---|---|
| Unity Editor | 6000.3.13f1 (Unity 6) |
| Unity CLI | 1.0.0-beta.2 |
| `com.unity.pipeline` | 0.3.1-exp.1 |
| OS | Windows 11 Pro |

Both the CLI and the package are experimental betas; expect drift. `unity command` / `GET /api/commands` reflect the installed version.

## Notes

- `com.unity.pipeline` is experimental; commands change between versions. `unity command` / `GET /api/commands` is the source of truth for the installed version.
- Server binds `127.0.0.1` only, bearer-token auth; token rotates on every domain reload.
- `eval` executes arbitrary C#. The runtime server is compile-guarded to development builds — do not attempt to enable it in release builds.
- Known doc corrections baked in: `/api/exec` body key is `parameters` (not `params`); token rotates on play-mode entry; `set_autotick` resets after domain reload; `get_console_logs` may return empty while the game runs (fall back to `Editor.log`).
