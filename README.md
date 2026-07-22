# unity-cli-editor-skill

A [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills) for driving a running **Unity Editor** (or development Player) from the CLI via the experimental **`com.unity.pipeline`** package — Unity's local HTTP command API.

With this skill, Claude Code can autonomously:

- open/save scenes, create GameObjects, attach components, edit serialized fields
- create and edit assets, prefabs, materials, animation clips, animator controllers, timelines
- enter/exit play mode, take screenshots of the Game/Scene view, read console logs
- force recompiles, run Unity tests, trigger builds, switch build targets
- manage UPM packages and project settings
- run arbitrary C# in the Editor via Roslyn `eval`, and hot-reload code in play mode

Distilled from the full [`com.unity.pipeline@0.3` manual](https://docs.unity3d.com/Packages/com.unity.pipeline@0.3/manual/index.html) (every guide + every command-reference page), plus field-tested gotchas the docs get wrong or omit (e.g. the `/api/exec` body key is `parameters`, not `params`; the auth token rotates on every domain reload including play-mode entry).

## Install

### 1. The skill

Clone into your project's skills folder:

```bash
git clone https://github.com/menstood/unity-cli-editor-skill.git .claude/skills/unity-cli-editor
```

Or for all projects, into your user skills folder:

```bash
git clone https://github.com/menstood/unity-cli-editor-skill.git ~/.claude/skills/unity-cli-editor
```

### 2. The Unity CLI (optional, but gives you the `unity` command)

The [Unity CLI](https://docs.unity.com/en-us/unity-cli) is a standalone experimental binary, independent of Unity Hub. Install per [Use the Unity CLI](https://docs.unity.com/en-us/unity-cli/use-unity-cli):

```bash
# macOS / Linux (Windows: run in a bash-capable shell such as Git Bash)
curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash
```

Then reopen your terminal and verify:

```bash
unity --version
unity auth login      # sign in to your Unity account
```

Update later with `unity upgrade`.

> The skill does not require the CLI — it talks to the same local HTTP API directly (see `SKILL.md` for the raw `curl`/PowerShell recipe). The CLI is just the nicest human front-end.

### 3. The `com.unity.pipeline` package (required, Unity 6.0+)

With the CLI, from your project folder while the project is open in the Editor:

```bash
unity pipeline install     # installs the package + dependencies into the project
unity pipeline list        # verify — should report "Pipeline: Installed"
```

Or manually without the CLI: Package Manager → *Install package by name* → `com.unity.pipeline` (e.g. `0.3.1-exp.1`), or add `"com.unity.pipeline": "0.3.1-exp.1"` to `Packages/manifest.json`.

Keep the Editor running with the project open — it starts the HTTP server and writes the port descriptor the skill connects to.

## Use

In Claude Code, just ask for anything that touches the Editor ("run the tests", "screenshot the game view", "why doesn't my scene load") — or invoke explicitly with `/unity-cli-editor`.

## Contents

- **`SKILL.md`** — entry point: connection recipe, auth, safety conventions (`confirm`/`dry_run`), async fire-and-poll patterns, common recipes, field-tested gotchas.
- **`references/commands-content.md`** — every content-authoring command with every parameter: assets & files, scenes, GameObjects & components, prefabs, scripts, animation, materials & shaders.
- **`references/commands-editor.md`** — baking, search & selection, capture, build/compile/tests, project settings, package manager, editor lifecycle & observability, runtime/player commands, hot reload.
- **`references/connectivity-and-setup.md`** — port descriptors, port ranges, token semantics, endpoints, dev-Player server setup, log locations.
- **`references/extending.md`** — writing custom `[CliCommand]`s, the authoring contract, hot-reload authoring, test architecture.

## Caveats

- `com.unity.pipeline` is **experimental**; command names/behavior may change between versions. The API is self-documenting — `GET /api/commands` is the source of truth for your installed version.
- The server binds loopback only and requires a bearer token, but `eval` executes arbitrary C# — never enable the runtime server in non-development builds (the package's compile guard prevents it).
