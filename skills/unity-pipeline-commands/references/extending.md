# Extending the pipeline: custom commands, method reload, tests (0.9.x)

## Creating commands

Every command has a **group** and a **name**, and clients run it as `<group> <name>`. Tag a **static** method (any accessibility) with `[CliGroupCommand]`, and its parameters with `[CliArg]`. `CommandRegistry` discovers commands through TypeCache in the Editor and reflection in a Player. There's **no manual registration**: new commands appear after a recompile.

```csharp
using Unity.Pipeline.Commands;

public static class MyCommands
{
    const string Group = "mytool";

    [CliGroupCommand(Group, "What this command does")]
    public static object Echo(
        [CliArg("text", "Some input", Required = true)] string text,
        [CliArg("count", "How many times")] int count = 1)
    {
        return new { echoed = text, count };   // -> {"success":true,"result":{...}}
    }
}
// unity command "mytool echo" --text hello --count 3
```

- `[CliGroupCommand(group, description, Name = ..., MainThreadRequired = true, Tags = ...)]`:
  - `group` is one or more `.`-separated segments (`asset`, `animation.animator`).
  - The name defaults to the method name in snake_case (`CreateController` → `create_controller`). **Renaming the method renames the command**, which is a breaking change. Use `Name =` only when the derived name is wrong.
  - `MainThreadRequired` defaults to true. Set it false only for thread-safe, read-only or pollable handlers.
  - `Tags` are path-style (`"assets/import"`). The `runtime` tag marks Player-targeting commands, which are also kept out of `job batch` on the Editor.
- `[CliCommand(group, name, description)]`, `[CliCommand("group.sub.name", description)]` (the last `.` splits group from name), or `[CliCommand(name, description)]` (no dot) all work too. The last form puts the command in the `global` group, runnable by its bare name. A method can't carry both attributes.
- The attributes live in `Unity.Pipeline.Attributes`, which has no define constraints. Response models, `IStructuredCommandInput` and `CommandRegistry` need a reference to `Unity.Pipeline`.
- `[CliArg(name, description, Required = ..., DefaultValue = ...)]`. `Required` defaults to "the C# parameter has no default". **Parameter declaration order and required-ness are wire API**: raw `argv`/`commandLine` clients bind positionals by order, so append new optional parameters at the end. Enum parameters are validated by name.
- **Timeouts:** declare `[CliArg("timeout", ...)] double timeoutInSeconds = 600` to change the 60 s default and receive the time left (positive infinity inside a detached job).
- **Return values:** a `string`, number, anonymous object, typed model, or `null`. The server wraps it in the lean envelope `{success, result}` (plus `error`, `errorDetails` and `warnings` when set; `"verbose": true` adds `command`, `executedAt` and `executionTimeMs`).
- **Multi-field args:** a DTO implementing `IStructuredCommandInput`. From a command line it's passed as JSON: `--payload '{"name":"x"}'`.
- **Failures via exceptions.** Never hand-build the envelope.
- **Dynamic registration:** `CommandRegistry.RegisterCommand(group, name, description, delegate, mainThreadRequired, tags)` and `UnregisterCommand(group, name)`. These are dropped on domain reload and on Play Mode exit, so re-register from `[InitializeOnLoadMethod]`.
- **Progress:** `CliProgress.Report(title, info, current, total, progress)` shows up in `GET /api/progress` and the CLI's progress bar. `CliEditorProgress.DisplayProgressBar` is a drop-in for `EditorUtility.DisplayProgressBar`.

## Authoring contract (commands that create/mutate content)

Key types (namespaces): `ProjectPaths`, `ObjectResolver`, `AuthoringUndoScope` in `Unity.Pipeline.Editor.Authoring`; `ObjectRef`, `AuthoringResult` in `Unity.Pipeline.Models`.

### 1. Paths — always through `ProjectPaths.Resolve`

```csharp
var normalized = ProjectPaths.Resolve(path, out var error);
if (normalized == null) throw new ArgumentException(error);
```

Bare paths → relative to authoring root; explicit `Assets/…`/`Packages/…` used as-is (still confined); absolute → project-relative; `..` or escapes → rejected (returns null + error).

### 2. Existing objects — `ObjectRef` in, resolve before mutating

```csharp
if (!ObjectResolver.TryResolve(target, out var obj, out var error))
    throw new ArgumentException(error);
```

Resolve *everything* before the first mutation to avoid partial changes.

### 3. Return identity — `AuthoringResult`

```csharp
var result = ObjectResolver.Describe(asset) ?? new AuthoringResult { Type = nameof(Material) };
result.AssetPath = assetPath;
return result;
```

Assets: `assetPath`, `guid`, `fileId`, `type`, `globalId`. Scene objects: `instanceId`, `hierarchyPath`, `type`, `globalId`.

### 4. Undo — one revertible step per command

```csharp
using (new AuthoringUndoScope("Set Material"))   // increments Undo group; CollapseUndoOperations on dispose
{
    Undo.RecordObject(renderer, "Set Material");
    renderer.sharedMaterial = material;
    EditorSceneManager.MarkSceneDirty(renderer.gameObject.scene);
}
```

| Mutation | Undo call |
|---|---|
| New scene object | `Undo.RegisterCreatedObjectUndo(obj, name)` |
| Modify fields | `Undo.RecordObject(obj, name)` **before** the change |
| Add component | `Undo.AddComponent(go, type)` |
| Reparent | `Undo.SetTransformParent(child, parent, name)` |
| Serialized props | `SerializedObject` + `ApplyModifiedProperties()` |

**Not undoable:** AssetDatabase ops (CreateAsset, SaveAsPrefabAsset, imports, folder creation, file writes), UPM changes, native-asset-backed settings — note "Not undoable via Ctrl+Z" in the command description.

### Safety convention (destructive/overwriting commands)

Expose `confirm` (default false) + `dry_run` (default false):
- `dry_run==true` → validate, describe intended change, mutate nothing, return preview — **wins even if confirm is also true**.
- `confirm==false` → refuse (throw `ArgumentException` or return structured error).
- `confirm==true` → perform. Non-destructive commands (e.g. `create_folder`) skip both.

```csharp
[CliGroupCommand(Group, "Clear baked lightmap data... Destructive: requires confirm=true (use dry_run to preview). Not undoable via Ctrl+Z.")]
public static object ClearBake(
    [CliArg("confirm", "Apply the clear...")] bool confirm = false,
    [CliArg("dry_run", "Preview what would be cleared...")] bool dryRun = false)
{
    if (dryRun) return new { status = "dry_run", wouldClear = true };
    if (!confirm) throw new ArgumentException("Refusing to clear baked lighting...");
    Lightmapping.Clear();
    return new { cleared = true };
}
```

### Authoring vs management commands

Management commands (settings/builds/packages) are lighter: unconfined paths allowed, no undo scope, return domain models (may return `{ success=false, code, error }`) instead of `AuthoringResult`.

### New-command checklist

- Editor-only, lives in `Editor/Commands/<Area>/` (namespace `Unity.Pipeline.Editor.Commands.<Area>`), static, `[CliGroupCommand]`-tagged with a `const string Group`
- All paths via `ProjectPaths.Resolve` (never string concatenation)
- Existing objects as `ObjectRef` via `ObjectResolver.TryResolve`; resolve before mutating
- Scene mutations inside `AuthoringUndoScope` with the matching `Undo` API
- AssetDatabase writes flagged non-undoable in the description
- Returns `AuthoringResult` (or model containing `AuthoringResult[]`)
- Failures via exceptions

## Method reload (live code changes)

Apply edited C# method bodies to running code without restarting Play mode or rebuilding. This replaces 0.3's `[HotReload]`/`[HotReloadWithOverrides]` and the `reload_file*` commands.

Tag the method with `[MethodReload]` **before** entering Play mode or building, because the dispatch check is woven in at compile time. The method must be `public` (instance or static) and return `void` or `IEnumerator`.

```csharp
using Unity.Pipeline.MethodReload;
using UnityEngine;

public class Spinner : MonoBehaviour
{
    public float rotationSpeed = 90f;

    [MethodReload]
    public void Update() => transform.Rotate(Vector3.up, rotationSpeed * Time.deltaTime);

    [OnMethodReloaded]          // optional: runs on every live instance after a reload lands
    void OnMethodReloaded() { }
}
```

| Command | Backend | Where |
|---|---|---|
| `script.methodreload reload <file>` | `Assembly.Load`, full C# | Editor Play mode, Desktop Mono dev builds (needs the runtime HTTP server in a Player). The reloaded body may use **public members only** |
| `script.methodreload reload_editor <file>` | IlInterpreter, C# subset | Editor. Use it to check an edit stays inside the interpreter's subset |
| `script.methodreload reload_player <file\|folder> [--player <id>]` | IlInterpreter | Connected dev Players over PlayerConnection, **including IL2CPP**. No HTTP server needed |

- `reload` parameters: `filename` (required), `timeout` (60 s), `assemblyDir` (also save the compiled assembly), `pdb` (portable PDB so breakpoints bind; compiles unoptimized).
- **The interpreter subset excludes:** `await`/`Task`, `try`/`catch`, `lock`, LINQ query syntax, `decimal`, `dynamic`, reflection types, `ref`/`out` params, generic methods, new type declarations, and static field declarations. Lambdas, closures, string interpolation and coroutine `yield` work. On IL2CPP only unstripped members are callable (`script.methodreload generate_link_xml`, then rebuild).
- **Reloadable:** new helper methods (not as entry points), delegates and method groups. A reloaded coroutine takes effect on the next `StartCoroutine`.
- **Watch mode:** Project Settings → Pipeline → Editor → Method Reload Interpreter Watch. Each save reloads automatically into the Editor, or pushes to connected Players. Auto-refresh is off while watching.
- **Supporting commands:** `script.methodreload status` (which methods have a reload applied) and `script.methodreload cleanup` (revert all and delete saved assemblies).

## Tests architecture

Two styles:
- **ViaClient** — spin up `PipelineTestServer`, call `server.Execute(command, params)`: full HTTP path, real routing + parameter coercion. Uses test port range **7850–7899** and **writes no descriptor** (won't clash with the live server on 7800–7849).
- **CommandDirect** — call the command's static method with typed args (no server overhead).

```csharp
[Test]
public void SetTransform_ViaClient_ArrayParams_Apply()
{
    var go = Track(new GameObject("Xform219_Arrays"));
    using (var server = new PipelineTestServer())
    {
        var response = server.Execute(CommandNames.GameobjectSetTransform, new {   // "gameobject set_transform"
            target = new { instanceId = PipelineUtils.GetObjectId(go) },
            position = new[] { 1f, 2f, 3f },
            rotation = new[] { 0f, 90f, 0f },
            scale = new[] { 2f, 2f, 2f }
        });
        Assert.IsTrue(response.IsSuccess, $"gameobject set_transform should succeed: {response.Error}");
        Assert.AreEqual(new Vector3(1, 2, 3), go.transform.localPosition);
    }
}
```

Helpers: `PipelineTestServer` (disposable; `Execute(command, parameters, timeoutMs = 30000)`), `TestEditorPipelineServer` (overrides port range/descriptor), `PipelineClient` (`ExecuteCommandAsync`, `GetStatusAsync`, `PostJsonAsync`), `EditorTestUtilities.WaitFor(cond, timeoutMs)`, `[assembly: LiveServerGuard]` (ITestAction asserting the live server descriptor/port/responsiveness is intact before/after tests).
