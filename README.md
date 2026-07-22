# unity-cli-editor-skill

A [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills) that lets Claude drive a **running Unity Editor** — open scenes, edit GameObjects, run tests, take screenshots, recompile, build — through Unity's local HTTP command API (the experimental [`com.unity.pipeline`](https://docs.unity3d.com/Packages/com.unity.pipeline@latest) package).

**Why:** Claude Code normally can't verify Unity work — it can't press Play, see the console, or run tests. With this skill it can do all of that itself.

## What Claude can do with it

| Area | Examples |
|---|---|
| Scenes & objects | open/save scenes, create GameObjects, attach components, edit fields |
| Assets | create/move/delete assets, prefabs, materials, animation clips, animators |
| Verify | enter Play mode, screenshot Game/Scene view, read console, run Unity tests |
| Build & compile | force recompile, trigger builds, switch targets, manage packages |
| Escape hatch | run arbitrary C# in the Editor (`eval`), hot-reload code in Play mode |

## Requirements

- **Unity 6.0+** with your project open in the Editor
- **Claude Code**
- *(Optional)* the [Unity CLI](https://docs.unity.com/en-us/unity-cli) — a nicer front-end; the skill also works without it by calling the HTTP API directly

## Installation

### Step 1 — Install the skill

For one project (run from the project root):

```bash
git clone https://github.com/menstood/unity-cli-editor-skill.git .claude/skills/unity-cli-editor
```

…or once for all your projects:

```bash
git clone https://github.com/menstood/unity-cli-editor-skill.git ~/.claude/skills/unity-cli-editor
```

### Step 2 — Add the `com.unity.pipeline` package to your Unity project

**Easiest (no CLI needed):** in the Unity Editor open **Window → Package Manager → + → Install package by name** and enter:

```
com.unity.pipeline
```

(Or add `"com.unity.pipeline": "0.3.1-exp.1"` to `Packages/manifest.json`.)

**Alternative (with the Unity CLI):**

```bash
unity auth login          # sign in once
unity pipeline install    # run from the project folder while the project is open
unity pipeline list       # verify → "Pipeline: Installed"
```

### Step 3 — Done. Try it

Keep the Editor running with your project open, then ask Claude Code anything that touches the Editor:

> "take a screenshot of the game view"
> "run the edit-mode tests"
> "why doesn't my scene load?"

…or invoke the skill explicitly with `/unity-cli-editor`.

<details>
<summary><b>Optional: install the Unity CLI</b></summary>

The [Unity CLI](https://docs.unity.com/en-us/unity-cli/use-unity-cli) is a standalone experimental binary (independent of Unity Hub). It handles server discovery and auth automatically, so Claude prefers it when present:

```bash
# macOS / Linux (Windows: run in a bash-capable shell such as Git Bash)
curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash
```

Reopen your terminal, then:

```bash
unity --version    # verify install
unity auth login   # sign in
unity command      # list every available Editor command
```

Update later with `unity upgrade`.

</details>

## How it works

The package runs a **loopback-only HTTP server inside the Editor** (ports 7800–7849) and writes a descriptor file with the port and a session token to `Library/Pipeline/`. The skill teaches Claude to find that server, authenticate, and call commands — plus the safety conventions (`confirm`/`dry_run`), async fire-and-poll patterns, and the gotchas the official docs get wrong (e.g. the request body key is `parameters`, not `params`; the token rotates on every domain reload).

## What's inside

| File | Contents |
|---|---|
| `SKILL.md` | Entry point: connection recipes (CLI + raw HTTP), safety rules, common workflows, field-tested gotchas |
| `references/commands-content.md` | Every authoring command: assets, scenes, GameObjects, prefabs, scripts, animation, materials |
| `references/commands-editor.md` | Baking, search, capture, build/tests, project settings, packages, editor lifecycle, runtime, hot reload |
| `references/connectivity-and-setup.md` | Port descriptors, tokens, endpoints, dev-Player server setup, log locations |
| `references/extending.md` | Writing custom `[CliCommand]`s, authoring contract, hot-reload authoring, test architecture |

## Good to know

- `com.unity.pipeline` is **experimental** — commands may change between versions. `unity command` (or `GET /api/commands`) is the source of truth for your installed version.
- The server binds `127.0.0.1` only and requires a bearer token, but `eval` executes arbitrary C# — never enable the runtime server outside development builds (the package's compile guard enforces this).
- Distilled from the full [`com.unity.pipeline@0.3` manual](https://docs.unity3d.com/Packages/com.unity.pipeline@0.3/manual/index.html) — every guide and command-reference page — then corrected against a live Editor.
