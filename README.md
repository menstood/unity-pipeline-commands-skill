# unity-pipeline-commands-skill

Agent skills for Unity work. Written for Claude Code (`SKILL.md` format), usable by any agent framework or human that reads markdown.

| Skill | What it does |
|---|---|
| [`unity-pipeline-commands`](skills/unity-pipeline-commands/SKILL.md) | Control a running Unity Editor (or development Player) through the local HTTP API of the experimental [`com.unity.pipeline`](https://docs.unity3d.com/Packages/com.unity.pipeline@latest) package: scene/asset/prefab authoring, play mode, screenshots, console logs, recompile, tests, builds, project settings, packages, C# eval, hot reload. |
| [`shader-teardown`](skills/shader-teardown/SKILL.md) | Break HLSL / ShaderLab code down into a Mermaid diagram of the equivalent Shader Graph (Blackboard, nodes, port-to-port wiring, Master Stack), checked against the Shader Graph docs for the project's exact Shader Graph version. |
| [`shadergraph-build`](skills/shadergraph-build/SKILL.md) | Turn a `shader-teardown` diagram into a real `.shadergraph` for the installed Shader Graph version, then verify it in the running Editor: compile messages, nodes/edges that survived loading, and a pixel comparison against the original shader. |

## Installation

Clone once, then copy (or symlink) the skill folders you want into a skills directory: `.claude/skills/` per project, or `~/.claude/skills/` globally.

```bash
git clone https://github.com/menstood/unity-pipeline-commands-skill.git
cp -r unity-pipeline-commands-skill/skills/unity-pipeline-commands .claude/skills/
cp -r unity-pipeline-commands-skill/skills/shader-teardown .claude/skills/
cp -r unity-pipeline-commands-skill/skills/shadergraph-build .claude/skills/
```

Windows (PowerShell):

```powershell
git clone https://github.com/menstood/unity-pipeline-commands-skill.git
Copy-Item -Recurse unity-pipeline-commands-skill\skills\unity-pipeline-commands .claude\skills\
Copy-Item -Recurse unity-pipeline-commands-skill\skills\shader-teardown .claude\skills\
Copy-Item -Recurse unity-pipeline-commands-skill\skills\shadergraph-build .claude\skills\
```

For non-Claude tooling, point your agent at the skill's `SKILL.md`.

---

## unity-pipeline-commands

`references/` doubles as a standalone API reference for the package, distilled from the full [`com.unity.pipeline@0.3` manual](https://docs.unity3d.com/Packages/com.unity.pipeline@0.3/manual/index.html) and corrected against a live Editor.

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
- Unity CLI: `unity command` lists all commands; `unity command <name> [--arg value ...]` executes.
- Raw HTTP: read `<project>/Library/Pipeline/.unity-pipeline-port` for port + token, then `POST http://127.0.0.1:<port>/api/exec` with `Authorization: Bearer <token>` and body `{"command":"<name>","parameters":{...}}`. Full recipe in its `SKILL.md`.

### Contents

| File | Contents |
|---|---|
| `SKILL.md` | Connection (CLI + raw HTTP), auth/token semantics, safety conventions (`confirm`/`dry_run`), async fire-and-poll patterns, common workflows, field-tested gotchas |
| `references/commands-content.md` | Authoring commands: assets & files, scenes, GameObjects & components, prefabs, scripts, animation, materials & shaders |
| `references/commands-editor.md` | Baking, search & selection, capture, build/compile/tests, project settings, package manager, editor lifecycle & observability, runtime commands, hot reload |
| `references/connectivity-and-setup.md` | Port descriptors, port ranges, token rotation, endpoints, dev-Player server setup, log locations |
| `references/extending.md` | Custom `[CliCommand]` authoring, authoring contract, hot-reload authoring, test architecture |

### Tested with

| Component | Version |
|---|---|
| Unity Editor | 6000.3.13f1 (Unity 6) |
| Unity CLI | 1.0.0-beta.2 |
| `com.unity.pipeline` | 0.3.1-exp.1 |
| OS | Windows 11 Pro |

Both the CLI and the package are experimental betas; expect drift. `unity command` / `GET /api/commands` reflect the installed version.

### Notes

- `com.unity.pipeline` is experimental; commands change between versions. `unity command` / `GET /api/commands` is the source of truth for the installed version.
- Server binds `127.0.0.1` only, bearer-token auth; token rotates on every domain reload.
- `eval` executes arbitrary C#. The runtime server is compile-guarded to development builds — do not attempt to enable it in release builds.
- Known doc corrections baked in: `/api/exec` body key is `parameters` (not `params`); token rotates on play-mode entry; `set_autotick` resets after domain reload; `get_console_logs` may return empty while the game runs (fall back to `Editor.log`).

---

## shader-teardown

Give it a `.shader`, `.hlsl` or `.cginc` file (or pasted shader code). It returns:

1. The Shader Graph version it used and where it found it (`Packages/packages-lock.json` first, then `manifest.json`, then a running Editor, otherwise it asks you).
2. A Mermaid flowchart: Blackboard properties → nodes → Master Stack blocks, with every edge labelled by the actual port names (`RGBA → A`).
3. A node table linking each node to its doc page for that version, e.g. `https://docs.unity3d.com/Packages/com.unity.shadergraph@17.3/manual/Lerp-Node.html`.
4. Notes on Custom Function nodes, keywords, and anything Shader Graph can't express.

Every node is checked against the version-matched docs. Node sets differ between versions (14.0 vs 17.x), and `@latest` doc URLs don't resolve.

| File | Contents |
|---|---|
| `SKILL.md` | Version pinning, shader reading, node verification, Mermaid conventions, output format |
| `references/hlsl-to-nodes.md` | Starting map from HLSL intrinsics and Unity macros to Shader Graph nodes and doc page names |

---

## shadergraph-build

The second half of `shader-teardown`: **HLSL → teardown diagram → `.shadergraph` → verified in the Editor.** Requires a running Unity Editor with `com.unity.pipeline` (see `unity-pipeline-commands`) and Python 3.

1. `SgCatalog.cs` asks the running Editor for every Shader Graph node of the installed version: slot IDs, port names, defaults, and the serialized form of every setting. Nothing about the file format is guessed.
2. `mermaid2sg.py` converts the teardown's Mermaid into one `.shadergraph` (URP Unlit). It takes display names, defaults and sliders from the original shader, and port types from the Custom Function HLSL. It stops on anything it can't map.
3. `GraphCheck.cs` imports the graph and checks compile messages, edges that survived loading, and nodes with errors.
4. `CompareShaders.cs` renders the original shader and the graph side by side under 5 light directions and reports pixel differences.

Tested on a ~290-node toon face shader (SDF face shadow, ramp, GGX, SDF rim) with Shader Graph 17.3 / Unity 6000.3: 0 compile messages, 383/383 edges loaded, mean pixel difference ~0.1% against the original HLSL.

| File | Contents |
|---|---|
| `SKILL.md` | Workflow, pass criteria, gotchas, limits |
| `scripts/SgCatalog.cs` | Editor-side node catalog dump |
| `scripts/mermaid2sg.py` | Mermaid → `.shadergraph` converter |
| `scripts/GraphCheck.cs` | Import + load check, generated HLSL dump |
| `scripts/CompareShaders.cs` | Original vs graph render comparison |
