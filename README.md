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

Clone into your project's skills folder:

```bash
git clone https://github.com/menstood/unity-cli-editor-skill.git .claude/skills/unity-cli
```

Or for all projects, into your user skills folder:

```bash
git clone https://github.com/menstood/unity-cli-editor-skill.git ~/.claude/skills/unity-cli
```

Then add the package to your Unity project (Unity 6+): Package Manager → *Add package by name* → `com.unity.pipeline` (e.g. `0.3.1-exp.1`). Keep the Editor running with the project open.

## Use

In Claude Code, just ask for anything that touches the Editor ("run the tests", "screenshot the game view", "why doesn't my scene load") — or invoke explicitly with `/unity-cli`.

## Contents

- **`SKILL.md`** — entry point: connection recipe, auth, safety conventions (`confirm`/`dry_run`), async fire-and-poll patterns, common recipes, field-tested gotchas.
- **`references/commands-content.md`** — every content-authoring command with every parameter: assets & files, scenes, GameObjects & components, prefabs, scripts, animation, materials & shaders.
- **`references/commands-editor.md`** — baking, search & selection, capture, build/compile/tests, project settings, package manager, editor lifecycle & observability, runtime/player commands, hot reload.
- **`references/connectivity-and-setup.md`** — port descriptors, port ranges, token semantics, endpoints, dev-Player server setup, log locations.
- **`references/extending.md`** — writing custom `[CliCommand]`s, the authoring contract, hot-reload authoring, test architecture.

## Caveats

- `com.unity.pipeline` is **experimental**; command names/behavior may change between versions. The API is self-documenting — `GET /api/commands` is the source of truth for your installed version.
- The server binds loopback only and requires a bearer token, but `eval` executes arbitrary C# — never enable the runtime server in non-development builds (the package's compile guard prevents it).
