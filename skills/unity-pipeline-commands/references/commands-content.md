# Content authoring commands

Conventions used below: **(req)** = required. `ObjectRef` = handle object with one of `globalId` / `path` / `guid`(+`fileId`) / `instanceId` / `hierarchyPath`. All return `AuthoringResult` unless noted. `confirm`/`dry_run` follow the standard safety convention (dry_run wins; confirm required to overwrite/destroy).

## Assets & files

| Command | Params | Notes |
|---|---|---|
| `create_asset` | `path` (req, with extension), `type` (req, UnityEngine.Object-derived type name), `shader` (Material-only), `confirm`, `dry_run` | confirm=true to overwrite existing |
| `import_asset` | `source` (req, absolute filesystem path), `path` (req, dest under authoring root), `confirm`, `dry_run` | Copies external file (texture/model/audio) into project |
| `move_asset` | `asset` (req, ObjectRef), `destination` (req, path with extension), `dry_run` | Move/rename; **preserves GUID**; dry_run uses `AssetDatabase.ValidateMoveAsset` |
| `copy_asset` | `asset` (req), `destination` (req), `confirm`, `dry_run` | Copy gets a **fresh GUID** |
| `rename_asset` | `asset` (req), `new_name` (req, filename only, extension preserved if omitted), `dry_run` | In-place, keeps folder + GUID |
| `delete_asset` | `asset` (req), `confirm` (must be true), `dry_run` | Destructive, **not undoable** |
| `find_assets` | `type`, `name`, `label`, `search_in` (folder scope), `limit` (default 200) | At least one of type/name/label required. Returns `FindAssetsResult` (path, GUID, type) |
| `set_import_settings` | `asset` (req), `settings` (req, JSON map of importer prop→value, e.g. `isReadable`), `dry_run` | Re-imports; lives in .meta, **not undoable**. Returns `SetImportSettingsResult` |
| `get_import_settings` | `asset` (req), `platform` (default `Default`) | Structured by importer type (texture/model/audio). Returns `GetImportSettingsResult` |
| `create_folder` | `path` (req) | Creates intermediates; no confirm/dry_run (non-destructive) |
| `read_text_file` | `path` (req), `max_bytes` (default 1048576) | UTF-8 under authoring root. Returns `ReadTextFileResult` |
| `write_text_file` | `path` (req, with extension), `contents` (req), `confirm`, `dry_run` | Writes then imports; confirm=true to overwrite; **not undoable** |

## Scenes

All mutating scene commands are **blocked during Play mode**. Scene `path` accepts optional `Assets/` prefix and `.unity` extension.

| Command | Params | Notes |
|---|---|---|
| `create_scene` | `path` (req), `additive` (default false), `template` (default `empty`; or `default` = Main Camera + Directional Light) | |
| `open_scene` | `path` (req), `additive` (default false) | |
| `save_scene` | `path` (optional; omit = active scene) | |
| `save_all` | — | Saves all dirty open scenes. Returns object |
| `list_open_scenes` | — | Load/active/dirty state per scene. Not play-blocked |
| `set_active_scene` | `path` (req, already-open scene) | New objects are created in the active scene |
| `get_scene_hierarchy` | `path` (optional; omit = active) | Returns `SceneHierarchy`; each node carries `instanceId` + `hierarchyPath` for GameObject commands. Not play-blocked |
| `add_scene_to_build` | `path` (req), `enabled` (default true) | Idempotent |
| `remove_scene_from_build` | `path` (req) | Idempotent |

## GameObjects & components

All are **Undo-able** and **blocked during Play mode** (reads excepted).

| Command | Params | Notes |
|---|---|---|
| `create_gameobject` | `name`, `primitive` (cube/sphere/capsule/cylinder/plane/quad), `parent` (ObjectRef) | Empty GO or primitive in active scene |
| `create_gameobjects` | `name` (base; suffixed Name1..NameN), `primitive`, `parent`, `count` (default 1), `positions`/`rotations`/`scales` (arrays of [x,y,z], length must equal count) | Batch; whole batch reverts as one Undo step. Returns `CreateGameObjectsResult` |
| `find_gameobjects` | `name` (exact), `tag`, `type` (component type), `hierarchy_path` (exact, e.g. `/Root/Child`), `include_inactive` (default true) | Filters combine (AND). Returns `FindGameObjectsResult` |
| `set_transform` | `target` (req), `position`/`rotation`/`scale` ([x,y,z]; rotation = local Euler degrees) | Omitted channels unchanged |
| `set_parent` | `target` (req), `parent` (omit = detach to scene root), `world_position_stays` (default true) | |
| `set_active` | `target` (req), `active` (req bool) | Sets activeSelf |
| `set_tag` | `target` (req), `tag` (req, must already exist in Tag Manager) | |
| `set_layer` | `target` (req), `layer` (req, name or index 0–31) | |
| `rename_gameobject` | `target` (req), `name` (req) | |
| `delete_gameobject` | `target` (req) | Undo-able; result describes identity captured before destruction |
| `add_component` | `target` (req), `type` (req, e.g. `Rigidbody` or `UnityEngine.Camera`) | |
| `remove_component` | `target` (req, component handle OR GameObject handle), `type` (omit if target is a component) | |
| `get_component_properties` | `target` (req, component or GO handle), `type` (omit if target is component) | Serialized props as JSON map. Returns `ComponentPropertiesResult` |
| `set_component_properties` | `target` (req), `properties` (req, map prop→value; vectors/colors as arrays; object refs as ObjectRef handles), `type` | One Undo step; **unknown property fails the whole batch (no partial apply)**. Returns `ComponentPropertiesResult` |

## Prefabs

| Command | Params | Notes |
|---|---|---|
| `create_prefab` | `source` (req, scene GO ref), `path` (req; `.prefab` added if missing) | Source becomes connected instance. Scene side Undo-able; **asset write not** |
| `instantiate_prefab` | `prefab` (req, asset ref), `scene_path` (default active scene), `name` (default prefab name) | Undo-able |
| `create_prefab_variant` | `base` (req, prefab asset ref), `path` (req) | Asset write not undoable |
| `apply_prefab_overrides` | `instance` (req, scene instance ref) | Pushes instance overrides to source asset (asset must be under authoring root); asset write not undoable |
| `revert_prefab_overrides` | `instance` (req) | Undo-able |
| `unpack_prefab` | `instance` (req), `completely` (default false = outermost level only) | Undo-able |
| `save_prefab_contents` | `prefab` (req), `rename_child` (relative path e.g. `Body/Head`), `new_name`, `set_active_child`, `active` (default true) | Declarative edit in isolated prefab stage (nested-prefab safe); prefab-stage save not undoable; asset must be under authoring root |

## Scripts & serialized fields

| Command | Params | Notes |
|---|---|---|
| `create_script` | `name` (req, class/file name, no extension), `path` (folder), `namespace`, `base_class` (default `MonoBehaviour`), `overwrite` (default false) | **Does not trigger recompile** — type unusable until a recompile completes (`recompile` + poll) |
| `attach_script` | `target` (req, GO ref), `type` XOR `script` (script asset path) — provide exactly one | Undo-able. Not-yet-compiled type → recoverable error |
| `set_serialized_field` | `target` (req, component or asset ref), `field` (req, SerializedProperty path), `value` (req, JSON), `component` (type name when target is a GO) | Primitives, enums, vectors, colors, object refs, array elements. Undo-able |
| `get_serialized_fields` | `target` (req), `field` (single prop path, optional), `component` | Names, types, values |

## Animation

### AnimationClips

| Command | Params | Notes |
|---|---|---|
| `create_animation_clip` | `path` (req, `.anim`), `frameRate` (default 60), `loop` (default false), `confirm`, `dry_run` | |
| `set_animation_curve` | `clip` (req), `path` (GO path relative to animated root, default ""), `type` (req, e.g. `Transform`), `property` (req, e.g. `m_LocalPosition.x`), `keys` (req, array of {time, value, inTangent?, outTangent?, weightedMode?}), `dry_run` | Replaces existing binding rather than duplicating. **Omitted tangents = 0 (flat), NOT Unity Auto tangent.** Returns `SetAnimationCurveResult` |
| `get_animation_clip` | `clip` (req), `includeKeys` (default false) | Metadata + float curve bindings. Returns `AnimationClipInfo` |
| `remove_animation_curve` | `clip` (req), `path` (default ""), `type` (req), `property` (req), `confirm` (must be true), `dry_run` | Destructive |

### AnimatorControllers

| Command | Params | Notes |
|---|---|---|
| `create_animator_controller` | `path` (req, `.controller`), `confirm`, `dry_run` | Creates with default Base Layer |
| `add_animator_parameter` | `controller` (req), `name` (req), `type` (req: Float/Int/Bool/Trigger), `defaultValue` (ignored for Trigger), `dry_run` | Duplicate name → code `duplicate_parameter` |
| `add_animator_layer` | `controller` (req), `name` (req), `weight` (default 1), `blendingMode` (default `Override`; or `Additive`), `dry_run` | |
| `add_animator_state` | `controller` (req), `layer` (index or name, default 0), `name` (req), `motion` (AnimationClip or BlendTree asset), `isDefault` (default false), `position` ([x,y], cosmetic), `dry_run` | Unmatched layer name → code `layer_not_found` |
| `add_animator_transition` | `controller` (req), `layer` (default 0), `fromState` (req; state name or `AnyState`/`Entry`), `toState` (req; state name or `Exit`), `conditions` (array of {parameter, mode: If/IfNot/Greater/Less/Equals/NotEqual, threshold?}), `hasExitTime` (default false), `exitTime` (0..1 normalized, default 0), `duration` (default 0.25), `hasFixedDuration` (default true = seconds, else normalized), `dry_run` | Validates states exist and each condition's parameter exists with matching mode/type |
| `get_animator_controller` | `controller` (req) | Full structure: parameters, layers, states (motion/default), transitions (conditions). Returns `AnimatorControllerInfo` |

### Timeline (requires `com.unity.timeline`)

| Command | Params | Notes |
|---|---|---|
| `create_timeline` | `path` (req, `.playable`), `frameRate` (default 60), `confirm`, `dry_run` | |
| `add_timeline_track` | `timeline` (req), `trackType` (req: Animation/Audio/Activation/Control/Playable/Signal/Marker), `name`, `parentTrack` (group/track name), `dry_run` | |
| `add_timeline_clip` | `timeline` (req), `track` (req, name), `start` (req, seconds), `duration` (req, seconds), `asset` (AnimationClip/AudioClip; required for Animation/Audio tracks), `dry_run` | |
| `get_timeline` | `timeline` (req) | Frame rate, duration, tracks with clips |

## Materials & shaders

| Command | Params | Notes |
|---|---|---|
| `get_material_properties` | `material` (req, ref) | Shader, render queue, enabled keywords, all shader properties. Returns `MaterialPropertiesResult` |
| `set_material_properties` | `material` (req), `shader` (name, optional reassign), `properties` (JSON map — **names need leading underscore**, e.g. `_BaseColor`; colors as `[r,g,b,a]` or hex), `renderQueue` (int), `enableKeywords`/`disableKeywords` (arrays), `confirm`, `dry_run` | Non-destructive and undoable. Returns `SetMaterialPropertiesResult` |
| `list_shaders` | `filter` (case-insensitive substring), `includeBuiltin` (default true), `limit` (default 200) | Discover valid shader names |
| `get_shader_properties` | `shader` (by name) XOR `material` (reads its shader) | Declared props: name, description, type, range, textureDimension, flags. Returns `ShaderPropertiesResult` |

Also: `create_material` (`path`, `shader` default `Standard`) exists as an authoring command (extension `.mat` auto-appended). For URP projects use e.g. `Universal Render Pipeline/Lit`, not `Standard` — check with `list_shaders`.
