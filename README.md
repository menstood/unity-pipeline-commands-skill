# unity-pipeline-commands-skill

> [!WARNING]
> **Deprecated and no longer maintained.** Unity now ships an official CLI and an official `unity-pipeline` agent skill that cover what `unity-pipeline-commands` did, and they stay in step with each Unity release. Please use those instead:
>
> - Unity CLI docs: [Use the Unity CLI](https://docs.unity.com/en-us/unity-cli/use-unity-cli) · [Command reference](https://docs.unity.com/en-us/unity-cli/unity-cli-reference)
> - Official agent skill: `unity upgrade`, then `unity pipeline install` in your project (installs the `unity-pipeline` skill), or `unity skill install <client> --skill unity-pipeline`
>
> The command syntax documented here targets the CLI 1.0 betas and Pipeline 0.9.x and may not match newer versions. The repository stays available, read-only, for reference.

Agent skills for Unity work. Written for Claude Code (`SKILL.md` format), usable by any agent framework or human that reads markdown.

| Skill | What it does |
|---|---|
| [`unity-pipeline-commands`](skills/unity-pipeline-commands/SKILL.md) | Control a running Unity Editor (or development Player) through the local HTTP API of the experimental [`com.unity.pipeline`](https://docs.unity3d.com/Packages/com.unity.pipeline@latest) package: scene/asset/prefab authoring, play mode, screenshots, console logs, recompile, tests, builds, project settings, packages, C# eval, hot reload. |

## Installation

Clone once, then copy (or symlink) the skill folders you want into a skills directory: `.claude/skills/` per project, or `~/.claude/skills/` globally.

```bash
git clone https://github.com/menstood/unity-pipeline-commands-skill.git
cp -r unity-pipeline-commands-skill/skills/unity-pipeline-commands .claude/skills/
```

Windows (PowerShell):

```powershell
git clone https://github.com/menstood/unity-pipeline-commands-skill.git
Copy-Item -Recurse unity-pipeline-commands-skill\skills\unity-pipeline-commands .claude\skills\
```

For non-Claude tooling, point your agent at the skill's `SKILL.md`.

---

## unity-pipeline-commands

Targets `com.unity.pipeline` **0.9.x**. `references/` doubles as a standalone API reference: the command tables are generated from a live 0.9.1 Editor's schema, and the connectivity/extending notes come from the package's bundled 0.9.1 docs, with behaviors re-checked against a live Editor.

### Requirements

- Unity 6.0+, project open in a running Editor
- `com.unity.pipeline` package installed in the project (below)
- Optional: [Unity CLI](https://docs.unity.com/en-us/unity-cli) — preferred client when present; otherwise the HTTP API is called directly

### Installing `com.unity.pipeline`

Without the Unity CLI: **Window → Package Manager → + → Install package by name** → `com.unity.pipeline` (leave version blank to get the latest).

With the Unity CLI, from the project folder while the project is open:

```bash
unity auth login
unity pipeline install
unity pipeline list        # verify: "Pipeline: Installed"
```

### Installing the Unity CLI (optional)

Windows (PowerShell):

```powershell
$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex
```

macOS / Linux:

```bash
curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash
```

Reopen terminal; verify with `unity --version`. Update with `unity upgrade`.

### Usage

- Claude Code: `/unity-pipeline-commands`, or any request that touches the Editor.
- Unity CLI: `unity command` lists command groups, `unity command <group>` lists a group's commands, and `unity command "<group> <name>" [--arg value ...]` executes. With CLI 1.0.0-beta.2, quote the full name.
- Raw HTTP: read `<project>/Library/Pipeline/.unity-pipeline-port` for port + token, then `POST http://127.0.0.1:<port>/api/exec` with `Authorization: Bearer <token>` and body `{"command":"<group> <name>","parameters":{...}}`. Full recipe in its `SKILL.md`.

### Contents

| File | Contents |
|---|---|
| `SKILL.md` | Connection (CLI + raw HTTP), token/descriptor lifecycle, readiness (503 busy), detached jobs, safety conventions (`confirm`/`dry_run`), async fire-and-poll patterns, common workflows, field-tested gotchas |
| `references/commands-content.md` | Authoring commands (generated): assets, scenes, GameObjects & components, prefabs, scripts & method reload, animation, materials |
| `references/commands-editor.md` | Editor commands (generated): build, capture, console, diagnostics, editor & play mode, jobs (batch/wait), baking, packages, runtime, project settings, tests |
| `references/connectivity-and-setup.md` | Descriptors, ports, auth, `/api/exec` request forms, readiness, detached jobs, Player server setup, log locations |
| `references/extending.md` | Custom `[CliGroupCommand]` authoring, authoring contract, method reload (`[MethodReload]`), test architecture |
| `scripts/gen_command_reference.py` | Regenerates the two command references from a running Editor after a package update |

### Tested with

| Component | Version |
|---|---|
| Unity Editor | 6000.3.13f1 (Unity 6) |
| Unity CLI | 1.0.0-beta.2 |
| `com.unity.pipeline` | 0.9.1-exp.1 |
| OS | Windows 11 Pro |

Both the CLI and the package are experimental betas; expect drift. `unity command` / `GET /api/commands` reflect the installed version.

### Notes

- `com.unity.pipeline` is experimental; commands change between versions. `unity command` / `GET /api/commands` is the source of truth for the installed version.
- Server binds `127.0.0.1` only, with bearer-token auth. Since 0.9 the token survives domain reloads and play mode, and changes only on Editor restart.
- `script eval` executes arbitrary C#. The Player server is opt-in per build type (Project Settings → Pipeline → Runtime). Don't enable it for release builds.
- Verified on 0.9.1: the `/api/exec` body key is `parameters` (`params` is silently ignored for optional args); 0.3 command names fail with a rename hint; the descriptor is deleted during domain reloads; the CLI (beta.2) stops waiting after ~30 s, so use detached jobs (`"job": true`) for long commands.
