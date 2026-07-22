# Extending the pipeline: custom commands, hot reload, tests

## Creating commands

Tag a **static** method with `[CliCommand]`; parameters with `[CliArg]`. `CommandRegistry` auto-discovers via TypeCache (Editor) or reflection (Player) — **no manual registration**; new commands appear after recompile.

```csharp
using Unity.Pipeline.Commands;

public static class MyCommands
{
    [CliCommand("my_command", "What this command does")]
    public static object MyCommand(
        [CliArg("text", "Some input", Required = true)] string text,
        [CliArg("count", "How many times")] int count = 1)
    {
        return new { echoed = text, count };
    }
}
```

- `[CliCommand(name, description, MainThreadRequired = true, RuntimeOnly = false)]` — `MainThreadRequired` defaults true (set false only for thread-safe read-only handlers); `RuntimeOnly=true` hides it from Editor listings.
- `[CliArg(name, description, Required = ..., DefaultValue = ...)]` — `Required` defaults from whether the C# param has a default value.
- Return: plain `string` (→ `result` field), a typed model extending `CommandExecutionResponse` (e.g. `EvalResponse`), any serializable object (auto-wrapped), or `null`. Envelope fields: `success`, `command`, `result`, `executionTimeMs`, `error`.
- Multi-field args: DTO implementing `IStructuredCommandInput`, members tagged `[CliArg]` / `[JsonProperty]` / implicit names; use **nullable types** for optional fields.
- **Failures via exceptions** — never hand-build the response envelope.

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
[CliCommand("clear_baked_lighting", "Clear baked lightmap data...")]
public static object ClearBakedLighting(
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

- Editor-only, lives in `Editor/Commands/<Area>/`, static, `[CliCommand]`-tagged
- All paths via `ProjectPaths.Resolve` (never string concatenation)
- Existing objects as `ObjectRef` via `ObjectResolver.TryResolve`; resolve before mutating
- Scene mutations inside `AuthoringUndoScope` with the matching `Undo` API
- AssetDatabase writes flagged non-undoable in the description
- Returns `AuthoringResult` (or model containing `AuthoringResult[]`)
- Failures via exceptions

## Hot reload

Apply edited C# to running code without restarting Play mode or rebuilding. **Editor Play Mode + Mono standalone dev builds only — never IL2CPP.**

### Flavor 1 — in-place (`reload_file`)

Tag methods `[HotReload]` (must be **public void instance** methods), edit the body, then:

```
unity command reload_file "<absolute path>/Spinner.cs"
unity command reload_file "<absolute path>/Spinner.cs" --pdb
```

```csharp
using Unity.Pipeline.HotReload;
public class Spinner : MonoBehaviour
{
    public float rotationSpeed = 90f;

    [HotReload]
    void Update() => transform.Rotate(Vector3.up, rotationSpeed * Time.deltaTime);
}
```

Params: `filename` (req), `timeout` (30000), `assemblyDir` (null), `pdb` (false — emits portable PDB, compiles unoptimized).

### Flavor 2 — override (`reload_file_override`)

Tag `[HotReloadWithOverrides]` and route through the helper; overrides live in a separate file as `public static <Ret> Name(<TargetType> instance, ...)`:

```csharp
public class BossController : MonoBehaviour
{
    [HotReloadWithOverrides]
    void Update() => HotReloadHelper.ExecuteWithHotReload(this, "Update", OriginalUpdate);
    public void OriginalUpdate() => transform.Rotate(45 * Time.deltaTime, 0, 0);
}

// BossOverrides.cs
public static class BossOverrides
{
    [HotReloadOverrideMethod("BossController.Update")]
    public static void TweakedUpdate(BossController instance)
        => instance.transform.Rotate(0, 90 * Time.deltaTime, 0);
}
```

Helper overloads: `ExecuteWithHotReload<T>(T instance, string methodName, Func<object>|Action originalMethod, params object[] parameters)`.

### How it works

1. **Roslyn compile** in-memory to IL (+ optional PDB), no disk writes by default.
2. **Load** via `PipelineUtils.LoadFromBytes` (`UnityEngine.Assemblies.CurrentAssemblies.LoadFromBytes` on 6000.5+, else `Assembly.Load`).
3. **Dispatch** through `HotReloadRegistry` keyed `TypeName.MethodName`.
4. `HotReloadInPlaceILPostProcessor` (Mono.Cecil) weaves a dispatch prologue into every `[HotReload]` method at build/compile time.

Support commands: `hotreload_status` (registry stats), `cleanup_hotreload` (remove old assemblies, clear registry).

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
        var response = server.Execute("set_transform", new {
            target = new { instanceId = PipelineUtils.GetObjectId(go) },
            position = new[] { 1f, 2f, 3f },
            rotation = new[] { 0f, 90f, 0f },
            scale = new[] { 2f, 2f, 2f }
        });
        Assert.IsTrue(response.IsSuccess, $"set_transform should succeed: {response.Error}");
        Assert.AreEqual(new Vector3(1, 2, 3), go.transform.localPosition);
    }
}
```

Helpers: `PipelineTestServer` (disposable; `Execute(command, parameters, timeoutMs = 30000)`), `TestEditorPipelineServer` (overrides port range/descriptor), `PipelineClient` (`ExecuteCommandAsync`, `GetStatusAsync`, `PostJsonAsync`), `EditorTestUtilities.WaitFor(cond, timeoutMs)`, `[assembly: LiveServerGuard]` (ITestAction asserting the live server descriptor/port/responsiveness is intact before/after tests).
