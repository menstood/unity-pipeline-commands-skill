# Authoring commands: assets, scenes, GameObjects, prefabs, scripts, animation, materials

Generated from the live command schema (`GET /api/commands`) of `com.unity.pipeline` **0.9.1-exp.1** on Unity 6000.3.13f1: 166 commands. Regenerate with `scripts/gen_command_reference.py` after a package update; `unity command <group>` / `GET /api/commands?group=<group>` is the source of truth for the installed version.

Run as `unity command "<group> <name>" --param value` (quote the full name with CLI 1.0.0-beta.2), or raw `POST /api/exec` `{"command": "<group> <name>", "parameters": {...}}`. **(req)** = required; `=x` = default. ObjectRef = `{"path"|"guid"+"fileId"|"instanceId"|"hierarchyPath"|"globalId": ...}`. Destructive commands follow the `confirm`/`dry_run` convention (see SKILL.md).

## `animation.animator`

| Command | Parameters | Description |
|---|---|---|
| `animation.animator add_layer` | `controller` ObjectRef **(req)**, `name` string **(req)**, `weight` float =1.0, `blendingMode` string =Override, `dry_run` bool =false | Add a layer to an AnimatorController. |
| `animation.animator add_parameter` | `controller` ObjectRef **(req)**, `name` string **(req)**, `type` string **(req)**, `defaultValue` JToken, `dry_run` bool =false | Add a parameter (Float \| Int \| Bool \| Trigger) to an AnimatorController. A duplicate name returns code 'duplicate_parameter'. |
| `animation.animator add_state` | `controller` ObjectRef **(req)**, `layer` JToken, `name` string **(req)**, `motion` ObjectRef, `isDefault` bool =false, `position` JArray, `dry_run` bool =false | Add a state to a layer, optionally with a motion (AnimationClip or BlendTree) and as the layer default. A layer name with no match returns code 'layer_not_found'. |
| `animation.animator add_transition` | `controller` ObjectRef **(req)**, `layer` JToken, `fromState` string **(req)**, `toState` string **(req)**, `conditions` JArray, `hasExitTime` bool =false, `exitTime` float =0.0, `duration` float =0.25, `hasFixedDuration` bool =true, `dry_run` bool =false | Add a transition between two states (or from AnyState/Entry, to Exit) on a layer, with optional conditions. Validates that the states exist and each condition's parameter exists and its mode matches the parameter type. |
| `animation.animator create_controller` | `path` string **(req)**, `confirm` bool =false, `dry_run` bool =false | Create an .controller AnimatorController asset (with a default Base Layer) under the authoring root. |
| `animation.animator get_controller` | `controller` ObjectRef **(req)** | Read an AnimatorController's full structure: parameters, layers, states (with motion / default), and transitions (with conditions). |

## `animation.clip`

| Command | Parameters | Description |
|---|---|---|
| `animation.clip create` | `path` string **(req)**, `frameRate` float =60.0, `loop` bool =false, `confirm` bool =false, `dry_run` bool =false | Create an empty .anim AnimationClip asset under the authoring root, with an optional frame rate and loop flag. |
| `animation.clip get` | `clip` ObjectRef **(req)**, `includeKeys` bool =false | Read an AnimationClip's metadata and all float curve bindings (optionally with keyframes). |
| `animation.clip remove_curve` | `clip` ObjectRef **(req)**, `path` string, `type` string **(req)**, `property` string **(req)**, `confirm` bool =false, `dry_run` bool =false | Remove a float curve binding from an AnimationClip (SetEditorCurve(clip, binding, null)). Destructive: requires confirm=true. |
| `animation.clip set_curve` | `clip` ObjectRef **(req)**, `path` string, `type` string **(req)**, `property` string **(req)**, `keys` JArray **(req)**, `dry_run` bool =false | Add or replace a single float curve binding on an AnimationClip (via AnimationUtility.SetEditorCurve). Replacing an existing binding overwrites it rather than duplicating. |

## `animation.timeline`

| Command | Parameters | Description |
|---|---|---|
| `animation.timeline add_clip` | `timeline` ObjectRef **(req)**, `track` string **(req)**, `start` float **(req)**, `duration` float **(req)**, `asset` ObjectRef, `dry_run` bool =false | Add a clip to a named track on a TimelineAsset. For Animation tracks pass an AnimationClip asset; for Audio tracks an AudioClip. Requires the com.unity.timeline package. |
| `animation.timeline add_track` | `timeline` ObjectRef **(req)**, `trackType` string **(req)**, `name` string, `parentTrack` string, `dry_run` bool =false | Add a track (Animation \| Audio \| Activation \| Control \| Playable \| Signal \| Marker) to a TimelineAsset, optionally nested under a parent group/track. Requires the com.unity.timeline package. |
| `animation.timeline create` | `path` string **(req)**, `frameRate` float =60.0, `confirm` bool =false, `dry_run` bool =false | Create a .playable TimelineAsset under the authoring root (optional frame rate). Requires the com.unity.timeline package. |
| `animation.timeline get` | `timeline` ObjectRef **(req)** | Read a TimelineAsset's structure: frame rate, duration, and its tracks with their clips. Requires the com.unity.timeline package. |

## `asset`

| Command | Parameters | Description |
|---|---|---|
| `asset copy` | `asset` ObjectRef **(req)**, `destination` string **(req)**, `confirm` bool =false, `dry_run` bool =false | Copy an asset to a new path under the authoring root. The copy gets a fresh GUID. |
| `asset create` | `path` string **(req)**, `type` string **(req)**, `shader` string, `confirm` bool =false, `dry_run` bool =false | Create a new ScriptableObject (or other UnityEngine.Object) asset of the given type at a path under the authoring root. |
| `asset create_folder` | `path` string **(req)** | Create a folder under the authoring root (creates intermediate folders). |
| `asset delete` | `asset` ObjectRef **(req)**, `confirm` bool =false, `dry_run` bool =false | Delete an asset from the project. Destructive: requires confirm=true. |
| `asset find` | `type` string, `name` string, `label` string, `search_in` string, `limit` int =200 | Find assets by type and/or name and/or label, returning their path, GUID and type. At least one filter is required. |
| `asset get_import_settings` | `asset` ObjectRef **(req)**, `platform` string =Default | Read an asset's import settings, structured by importer type (texture/model/audio), including the default-platform fields and (for textures/audio) one platform override block. |
| `asset import` | `source` string **(req)**, `path` string **(req)**, `confirm` bool =false, `dry_run` bool =false | Import an external file (e.g. a texture, model, audio clip) into the project by copying it to a path under the authoring root, then importing it. |
| `asset move` | `asset` ObjectRef **(req)**, `destination` string **(req)**, `dry_run` bool =false | Move (or rename via a new path) an asset to a new location under the authoring root. Preserves the asset's GUID. |
| `asset read_text` | `path` string **(req)**, `max_bytes` int =1048576 | Read a UTF-8 text file under the authoring root and return its contents. |
| `asset rename` | `asset` ObjectRef **(req)**, `new_name` string **(req)**, `dry_run` bool =false | Rename an asset in place (keeps it in the same folder, keeps its GUID). |
| `asset set_import_settings` | `asset` ObjectRef **(req)**, `settings` JObject **(req)**, `platform` string =Default, `dry_run` bool =false | Set import settings on an asset's AssetImporter (default platform top-level properties, or a texture/audio per-platform override) and re-import it. |
| `asset write_text` | `path` string **(req)**, `contents` string **(req)**, `confirm` bool =false, `dry_run` bool =false | Write UTF-8 text to a file under the authoring root, then import it. Overwriting an existing file requires confirm=true. |

## `authoring`

| Command | Parameters | Description |
|---|---|---|
| `authoring get_root` | — | Get the base folder (under Assets/) that bare authoring paths resolve against. |
| `authoring set_root` | `root` string **(req)** | Set the base folder (under Assets/) that bare authoring paths resolve against and are confined to. Use 'Assets' for full project access. |

## `component`

| Command | Parameters | Description |
|---|---|---|
| `component add` | `target` ObjectRef **(req)**, `type` string **(req)** | Add a component (by type name) to a GameObject. |
| `component get_fields` | `target` ObjectRef **(req)**, `field` string, `component` string, `format` string | Read serialized fields of a component/asset. Returns each top-level field's name, type and value (object references are returned as re-usable handles). Pass 'field' to read a single SerializedProperty path. Pass format='value' to return just the value(s) — a token-efficient read for scalars. |
| `component get_properties` | `target` ObjectRef **(req)**, `type` string | Get a component's serialized properties as a JSON map. Address the component by handle, or by GameObject handle + type. |
| `component remove` | `target` ObjectRef **(req)**, `type` string | Remove a component from a GameObject. Provide either a component handle (target) or a GameObject handle (target) plus a type name. |
| `component set_field` | `target` ObjectRef **(req)**, `field` string **(req)**, `value` JToken **(req)**, `component` string | Set a serialized field on a component/asset. Supports primitives, enums, Vector/Color/Rect/Bounds, object references (value = an ObjectRef: asset by guid/fileId/path or scene object by instanceId/hierarchyPath), and array elements via 'name.Array.data[i]' (or 'name.Array.size' to resize). |
| `component set_properties` | `target` ObjectRef **(req)**, `properties` JObject **(req)**, `type` string | Set serialized properties on a component (one Undo step). 'properties' maps property name -> value; object references accept an ObjectRef handle. |

## `gameobject`

| Command | Parameters | Description |
|---|---|---|
| `gameobject create` | `name` string, `primitive` string, `parent` ObjectRef | Create an empty GameObject or a built-in primitive (cube/sphere/capsule/cylinder/plane/quad) in the active scene. |
| `gameobject create_many` | `name` string, `primitive` string, `parent` ObjectRef, `count` int =1, `positions` Single[][], `rotations` Single[][], `scales` Single[][] | Batch-create N empty GameObjects or primitives in one call. Optional positions/rotations/scales are arrays of [x,y,z] (length must equal count). Returns the created identities. |
| `gameobject delete` | `target` ObjectRef **(req)** | Delete a GameObject from the scene (reversible via Undo). |
| `gameobject find` | `name` string, `tag` string, `type` string, `hierarchy_path` string, `include_inactive` bool =true | Find GameObjects in loaded scenes by name, tag, component type, and/or hierarchy path (filters are combined). Returns structured identities. |
| `gameobject get_selection` | — | Read the current Editor selection as structured object identities. |
| `gameobject rename` | `target` ObjectRef **(req)**, `name` string **(req)** | Rename a GameObject. |
| `gameobject set_active` | `target` ObjectRef **(req)**, `active` bool **(req)** | Set a GameObject's active self-state (activeSelf). |
| `gameobject set_layer` | `target` ObjectRef **(req)**, `layer` string **(req)** | Set a GameObject's layer by name or numeric index (0-31). |
| `gameobject set_parent` | `target` ObjectRef **(req)**, `parent` ObjectRef, `world_position_stays` bool =true | Reparent a GameObject under a new parent, or detach it to scene root when no parent is given. |
| `gameobject set_selection` | `instance_ids` ObjectId[], `paths` string[] | Set the Editor selection to the given assets/scene objects. |
| `gameobject set_tag` | `target` ObjectRef **(req)**, `tag` string **(req)** | Set a GameObject's tag (the tag must already exist in the project). |
| `gameobject set_transform` | `target` ObjectRef **(req)**, `position` float[], `rotation` float[], `scale` float[] | Set a GameObject's local position/rotation(euler)/scale. Omitted channels are left unchanged. |

## `material`

| Command | Parameters | Description |
|---|---|---|
| `material get_properties` | `material` ObjectRef **(req)** | Read a material's shader, render queue, enabled keywords, and all shader properties with their current values (Color as [r,g,b,a], Vector as [x,y,z,w], Texture as an object reference). |
| `material get_shader_properties` | `shader` string, `material` ObjectRef | Introspect a shader's declared property list (name, description, type Color\|Vector\|Float\|Range\|TexEnv\|Int, range, textureDimension, flags). Provide 'shader' (by name) OR 'material' (read the shader off that material). |
| `material list_shaders` | `filter` string, `includeBuiltin` bool =true, `limit` int =200 | Discover available shaders so an agent can pick a valid name for material set_properties / asset create. Returns [{ name, assetPath\|null, isBuiltin, isSupported }]. |
| `material set_properties` | `material` ObjectRef **(req)**, `shader` string, `properties` JObject, `renderQueue` Nullable`1, `enableKeywords` string[], `disableKeywords` string[], `confirm` bool =false, `dry_run` bool =false | Set shader properties on a material (Float/Range/Int=number; Color=[r,g,b,a] or "#RRGGBBAA" hex; Vector=[x,y,z,w]; Texture=an object reference or null to clear), optionally reassign the shader, set the render queue, and toggle keywords. Unknown names / type mismatches are reported in unknown[]. |

## `prefab`

| Command | Parameters | Description |
|---|---|---|
| `prefab apply_overrides` | `instance` ObjectRef **(req)** | Apply a prefab instance's overrides back to its source prefab asset. |
| `prefab create` | `source` ObjectRef **(req)**, `path` string **(req)** | Save a GameObject as a prefab asset at a project path; the source becomes a connected instance. |
| `prefab create_variant` | `base` ObjectRef **(req)**, `path` string **(req)** | Create a prefab variant asset that inherits from a base prefab. |
| `prefab instantiate` | `prefab` ObjectRef **(req)**, `scene_path` string, `name` string | Instantiate a prefab asset into a loaded scene and return the created instance. |
| `prefab revert_overrides` | `instance` ObjectRef **(req)** | Revert a prefab instance's overrides so it matches its source prefab asset. |
| `prefab save_contents` | `prefab` ObjectRef **(req)**, `rename_child` string, `new_name` string, `set_active_child` string, `active` bool =true | Open a prefab asset in an isolated prefab stage, apply a declarative edit, and save it back (nested-prefab safe). |
| `prefab unpack` | `instance` ObjectRef **(req)**, `completely` bool =false | Unpack a prefab instance into plain GameObjects (outermost level or completely). |

## `scene`

| Command | Parameters | Description |
|---|---|---|
| `scene add_to_build` | `path` string **(req)**, `enabled` bool =true | Add a scene to the Build Settings scene list (idempotent). Optionally enable it. |
| `scene create` | `path` string **(req)**, `additive` bool =false, `template` string =empty | Create a new scene and save it to the given path under the authoring root. |
| `scene get_hierarchy` | `path` string | Return the GameObject tree of an open scene (or the active scene). Each node carries instanceId + hierarchyPath usable by GameObject commands. |
| `scene list_open` | — | List all currently open scenes with their load/active/dirty state. |
| `scene open` | `path` string **(req)**, `additive` bool =false | Open an existing scene from the given path. |
| `scene remove_from_build` | `path` string **(req)** | Remove a scene from the Build Settings scene list (idempotent). |
| `scene save` | `path` string | Save an open scene. Saves the active scene when no path is given. |
| `scene set_active` | `path` string **(req)** | Set which open scene is the active scene (new objects are created in the active scene). |

## `script`

| Command | Parameters | Description |
|---|---|---|
| `script attach` | `target` ObjectRef **(req)**, `type` string, `script` string | Add a MonoBehaviour to a GameObject by its (compiled) type name OR by its script asset path. Provide exactly one of 'type' or 'script'. If the type isn't compiled yet, returns a recoverable error: script recompile, poll script recompile_status, then retry. |
| `script create` | `name` string **(req)**, `path` string, `namespace` string, `base_class` string =MonoBehaviour, `overwrite` bool =false | Create a new C# script (default base class MonoBehaviour) from a template under the authoring root. NOTE: the type does not exist until a recompile completes — to attach it, call script recompile, poll script recompile_status, then script attach. |
| `script eval` | `code` string **(req)**, `timeout` double =30.0 | Evaluate C# code dynamically using Roslyn compiler |
| `script eval_file` | `file` string **(req)**, `timeout` double =30.0 | Evaluate C# code read from a .cs file on disk |
| `script recompile` | `focus` bool =false | Force a script recompile (works while unfocused/minimized). Poll script recompile_status for completion. |
| `script recompile_status` | — | Get the status of the last recompile: idle \| triggered \| compiling \| completed \| up_to_date. |
| `script run` | `file` string **(req)**, `entry` string, `args` JArray, `mode` string =ephemeral, `references` string[], `defines` string[], `pdb` bool =false, `timeout` double =60.0, `dry_run` bool =false | Compile a project C# file in memory (no domain reload) and execute a named static entry point. The builder-pattern path for bulk construction. Still arbitrary code execution — shares script eval's capability gate. |

## `script.methodreload`

| Command | Parameters | Description |
|---|---|---|
| `script.methodreload cleanup` | `assemblyDir` string **(req)**, `force_domain_reload` bool =true | Remove old method reload DLL versions and clear registry |
| `script.methodreload generate_link_xml` | `delete` bool =false | Generate ProjectSettings/Packages/com.unity.pipeline/MethodReload.link.xml: per-type preservation of the engine/package types the game's assemblies reference and of the game's own types, plus the interpreter's host surface and [MethodReload] targets. Applied to IL2CPP development builds only, while the Pipeline is enabled in development builds. Pass delete=true to remove the file instead. |
| `script.methodreload reload` | `filename` string **(req)**, `timeout` double =60.0, `assemblyDir` string, `pdb` bool =false | Compile and apply in-place [MethodReload] edits from a source file |
| `script.methodreload reload_editor` | `filename` string **(req)**, `timeout` double =60.0, `assemblyDir` string, `pdb` bool =false | Compile in-place [MethodReload] edits and run them through the IlInterpreter VM in this process instead of Assembly.Load (IL2CPP-safe; only a minimal host API + the target type are available) |
| `script.methodreload reload_player` | `filename` string **(req)**, `player` int =-1 | Compile a file's (or folder's) [MethodReload] method(s) and push the IL to a connected player (IL2CPP-safe) over PlayerConnection. Folders are walked recursively and pushed once. |
| `script.methodreload status` | — | Show current method reload registry status and statistics |
