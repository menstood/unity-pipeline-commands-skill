---
name: shadergraph-build
description: Build a real Unity Shader Graph (.shadergraph) from a shader-teardown Mermaid diagram, then verify it in the running Editor (import, compile messages, nodes/edges that survived loading) and, when the original HLSL shader is available, compare both renders pixel by pixel. Use after shader-teardown when the user wants the graph created, not just diagrammed. Needs a running Unity Editor with com.unity.pipeline (see unity-pipeline-commands) and Python 3.
---

# Shader Graph build — Mermaid → .shadergraph → verified

Turns the Mermaid produced by **shader-teardown** into a `.shadergraph` for the project's exact Shader Graph version, and proves it works. Nothing is hand-typed from memory: node classes, slot IDs, port names, defaults and setting values all come from the running Editor.

Scripts are in `scripts/`:

| Script | Runs in | Does |
|---|---|---|
| `SgCatalog.cs` | Editor (`eval_file`) | Dumps every Shader Graph node of the installed version to `Temp/sg_catalog.json`: class, slots (id, name, direction, serialized JSON) and, for every UI setting, the node JSON each value produces |
| `mermaid2sg.py` | Python | Converts the teardown's Mermaid diagrams into one `.shadergraph`. Fails loudly on any node, port or setting it can't map |
| `GraphCheck.cs` | Editor (`eval_file`) | Imports the graph, reports compile messages, loads it through Shader Graph's importer and counts nodes / edges / nodes with errors, writes the generated HLSL to `Temp/` |
| `CompareShaders.cs` | Editor (`eval_file`) | Renders the original shader and the graph on the same sphere under 5 light directions, reports pixel differences, saves an original / graph / diff sheet |

## Before you start

- **Ask before writing into the project.** Put everything in one new folder (e.g. `Assets/_ShaderGraphBuild/`). If the project isn't under version control, say so, and offer `git init` with a Unity `.gitignore` plus a baseline commit, so the work can be reverted.
- Pipeline connection, CLI syntax and safety rules come from **unity-pipeline-commands**. With pipeline 0.9.x and CLI 1.0.0-beta.2, grouped command names must be quoted: `unity command "console get"`, `unity command "editor set_auto_tick" --enable true`.
- Turn on auto-tick first, so the Editor keeps working while it's in the background.
- The CLI waits only about 30 s. Every Editor script here also writes its result to a `Temp/sgbuild_*_result.txt` file. If the CLI times out (first renders compile shader variants), wait for that file instead of re-running.

## 1. Node catalog (once per Shader Graph version)

```bash
unity command eval_file --file <skill>/scripts/SgCatalog.cs --timeout 60000
cp <project>/Temp/sg_catalog.json <work dir>/
```

Expect about 200 nodes and 0 failures (17.3 has 205). Re-dump whenever the Shader Graph version changes.

## 2. Prepare the inputs

- **Mermaid:** the teardown markdown. Every ```` ```mermaid ```` block is read, and diagrams are stitched through `[["NAME"]]` boxes. It must follow shader-teardown's conventions: exact node names, `Key: value` settings, port names on every edge.
- **Property hints** for anything the original `Properties` block doesn't cover: `= (x,y,z)` default, `hidden` (exposed but `[HideInInspector]`, for values set from script), `normal` (bump default texture).
- **Custom Function file:** write the teardown's HLSL into the project folder as a `.hlsl` file. Functions must be named `<Name>_float` and guarded with `#if defined(SHADERGRAPH_PREVIEW) || !defined(UNIVERSAL_PIPELINE_CORE_INCLUDED)` plus a fallback branch. Import it, then read its GUID: `AssetDatabase.AssetPathToGUID(path)` via `eval`.
- **Display names (optional):** a JSON `{ "_Ref": "Display Name" }` file. Use it when the source labels are in a language the user can't read, or are unclear. Offer translations; don't silently keep foreign-language labels.

## 3. Convert

```bash
PYTHONIOENCODING=utf-8 python -I <skill>/scripts/mermaid2sg.py \
  --md teardown.md --catalog sg_catalog.json \
  --samples "<project>/Library/PackageCache/com.unity.shadergraph@<hash>" \
  --shader Original.shader \          # display names, defaults, Range sliders
  --hlsl <project>/Assets/.../Funcs.hlsl --hlsl-guid <guid> \
  --names names.json \                # optional display-name overrides
  --out Name.shadergraph
```

Then copy the file into the project folder. `--samples` supplies Unity's own serialized templates for properties, property nodes, the URP target and the Master Stack blocks. On failure, the converter lists every problem (unknown node, missing port, bad setting) and writes nothing. Fix the Mermaid, don't patch the output.

## 4. Check

Write `Temp/sgbuild_check.txt` containing `graph=Assets/.../Name.shadergraph`, then run `GraphCheck.cs`. Pass criteria:

- `messages=0` and an empty console (`unity command "console get"`)
- the loaded **edge count equals the converter's edge count** (Shader Graph drops edges it doesn't accept, silently)
- `nodesWithError=0`
- the property list shows the expected reference names, display names, and `[hidden]` flags

## 5. Compare with the original (when the HLSL shader is in the project)

Write `Temp/sgbuild_compare.txt` (format in the script header: `original=`, `graph=`, then `texture` / `float` / `color` / `vector` overrides), then run `CompareShaders.cs`. Use real textures where you have them, and solid-color masks to force specific branches (e.g. a refine mask with G = 0 so an SDF path runs everywhere). Read the sheet image.

What to expect from a correct graph is a mean difference well under 1% and no pixel above 5%. Small leftovers concentrated in a highlight usually come from Shader Graph renormalizing interpolated normals per pixel. Large or uniform differences mean a real bug (see Gotchas).

## 6. Assign to a material (if asked)

Switching a material's shader keeps values for matching reference names. Set textures and values, `EditorUtility.SetDirty`, `AssetDatabase.SaveAssets`, then **read the values back from the `.mat` file**. Then screenshot (`unity command screenshot --view scene`) after framing with `SceneView.LookAt`. Script-driven values (head direction etc.) are a snapshot. Say that the original's per-frame setter script is needed for animation.

## Gotchas (all hit in practice)

- **Settings must be explicit.** A template node carries whatever its sample used. A Sample Texture 2D copied as *Type: Normal* ran `UnpackNormal` and zeroed blue. The catalog gives clean defaults, and the converter applies every setting from the label.
- **Silent edge loss.** A wrong node key made every Custom Function edge disappear, and the graph still compiled. Always compare edge counts (step 4) and render (step 5).
- **Un-exposed properties can't be saved.** A property with Exposed off isn't in the Properties block, so the material drops values set from script. Use `hidden` (exposed + `[HideInInspector]`).
- **Write after reimport, then verify on disk.** Setting a material value right after its shader reimports can be lost. Read the `.mat` back.
- **sRGB colors in pixel tests.** `Material.SetColor` converts to linear in a linear-space project (0.5 → 0.214). Compute expected values with `Color.linear`.
- **Dynamic vectors** resolve to the *smallest* connected width (Float excluded), so a Vector 4 Color into a Vector 3 path is truncated automatically. `(.xyz)` edge hints don't need Swizzle nodes.
- **Your own failed commands show up as console errors.** Clear the console (`"console clear"`) before each check.
- **Windows:** run Python with `PYTHONIOENCODING=utf-8`. Labels contain `→` and may contain non-ASCII display names.

## Limits

- Target: URP **Unlit**, Opaque, one graph (no Sub Graphs, no Keywords yet). Node layout is automatic (columns by distance to the output), so it's readable but not pretty.
- Custom Functions: File mode, float/float2/float3/float4 ports.
- Properties: Texture2D, Color, Float (Range → slider), Vector2/3/4.
