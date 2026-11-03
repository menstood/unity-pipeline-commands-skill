# HLSL → Shader Graph node map

This is a **starting map, not a source of truth.** Node names, port names and availability change between Shader Graph versions. Verify every node you use at `https://docs.unity3d.com/Packages/com.unity.shadergraph@<major.minor>/manual/<Node-Name>-Node.html` for the pinned version (see SKILL.md §1, §3).

The doc page column is the expected `<Node-Name>-Node.html` filename. If it 404s, look the node up through `Node-Library.html` → category page.

## Math: basic

| HLSL | Node | Doc page |
|---|---|---|
| `a + b` | Add | `Add-Node.html` |
| `a - b` | Subtract | `Subtract-Node.html` |
| `a * b` (component-wise) | Multiply | `Multiply-Node.html` |
| `mul(m, v)` | Multiply (matrix × vector), or Transform when it's a space change | `Multiply-Node.html` |
| `a / b` | Divide | `Divide-Node.html` |
| `pow(a, b)` | Power | `Power-Node.html` |
| `sqrt(x)` | Square Root | `Square-Root-Node.html` |
| `rcp(x)` / `1 / x` | Reciprocal | `Reciprocal-Node.html` |
| `fmod(a, b)` | Modulo | `Modulo-Node.html` |
| `-x` | Negate | `Negate-Node.html` |
| `1 - x` | One Minus | `One-Minus-Node.html` |

## Math: range & rounding

| HLSL | Node | Doc page |
|---|---|---|
| `saturate(x)` | Saturate | `Saturate-Node.html` |
| `clamp(x, a, b)` | Clamp | `Clamp-Node.html` |
| `min` / `max` | Minimum / Maximum | `Minimum-Node.html` / `Maximum-Node.html` |
| `abs(x)` | Absolute | `Absolute-Node.html` |
| `sign(x)` | Sign | `Sign-Node.html` |
| `floor` / `ceil` / `round` / `trunc` | Floor / Ceiling / Round / Truncate | `Floor-Node.html` / `Ceiling-Node.html` / `Round-Node.html` / `Truncate-Node.html` |
| `frac(x)` | Fraction | `Fraction-Node.html` |
| remap `(x - a) / (b - a) * (d - c) + c` | Remap | `Remap-Node.html` |

## Math: interpolation

| HLSL | Node | Doc page |
|---|---|---|
| `lerp(a, b, t)` | Lerp | `Lerp-Node.html` |
| `(x - a) / (b - a)` | Inverse Lerp | `Inverse-Lerp-Node.html` |
| `smoothstep(a, b, x)` | Smoothstep | `Smoothstep-Node.html` |
| `step(edge, x)` | Step | `Step-Node.html` |

## Math: vector

| HLSL | Node | Doc page |
|---|---|---|
| `dot(a, b)` | Dot Product | `Dot-Product-Node.html` |
| `cross(a, b)` | Cross Product | `Cross-Product-Node.html` |
| `normalize(v)` | Normalize | `Normalize-Node.html` |
| `length(v)` | Length | `Length-Node.html` |
| `distance(a, b)` | Distance | `Distance-Node.html` |
| `reflect(i, n)` | Reflection | `Reflection-Node.html` |
| `refract(i, n, eta)` | Refract | `Refract-Node.html` |
| `TransformObjectToWorld` etc. (explicit, as part of the effect) | Transform | `Transform-Node.html` |

## Math: trig, exp, derivatives

| HLSL | Node | Doc page |
|---|---|---|
| `sin` / `cos` / `tan` | Sine / Cosine / Tangent | `Sine-Node.html` / `Cosine-Node.html` / `Tangent-Node.html` |
| `asin` / `acos` / `atan` / `atan2` | Arcsine / Arccosine / Arctangent / Arctangent2 | `Arcsine-Node.html` / `Arccosine-Node.html` / `Arctangent-Node.html` / `Arctangent2-Node.html` |
| `exp` / `exp2` | Exponential (Base setting) | `Exponential-Node.html` |
| `log` / `log2` / `log10` | Log (Base setting) | `Log-Node.html` |
| `ddx` / `ddy` / `fwidth` | DDX / DDY / DDXY | `DDX-Node.html` / `DDY-Node.html` / `DDXY-Node.html` |

## Channel / swizzle

| HLSL | Node | Doc page |
|---|---|---|
| `v.x`, `v.rgb` (reading channels) | Split (single channels) or Swizzle | `Split-Node.html` / `Swizzle-Node.html` |
| `float4(a, b, c, d)` | Combine, or Vector 2/3/4 | `Combine-Node.html` / `Vector-4-Node.html` |
| `v.yxzw` (reorder) | Swizzle | `Swizzle-Node.html` |

## Logic

| HLSL | Node | Doc page |
|---|---|---|
| `c ? a : b` / `if` choosing a value | Branch (+ Comparison for the condition) | `Branch-Node.html` / `Comparison-Node.html` |
| `clip(x)` | No node. Use **Alpha Clipping** in Graph Settings + Alpha / Alpha Clip Threshold blocks | — |
| `#if KEYWORD` | Keyword node (Blackboard) | `Keyword-Node.html` |

## Inputs (built-in values)

| HLSL / macro | Node | Doc page |
|---|---|---|
| `i.uv`, `TRANSFORM_TEX(uv, _Tex)` | UV (+ Tiling And Offset for `_ST`) | `UV-Node.html` / `Tiling-And-Offset-Node.html` |
| `_Time.y`, `_SinTime`, `_CosTime` | Time | `Time-Node.html` |
| object / world / view position | Position (Space setting) | `Position-Node.html` |
| normal / tangent / bitangent | Normal Vector / Tangent Vector / Bitangent Vector | `Normal-Vector-Node.html` / `Tangent-Vector-Node.html` / `Bitangent-Vector-Node.html` |
| view direction (`GetWorldSpaceViewDir`, `_WorldSpaceCameraPos - posWS`) | View Direction / View Vector (check which exists and which normalizes in this version) | `View-Direction-Node.html` / `View-Vector-Node.html` |
| `i.color` (vertex color) | Vertex Color | `Vertex-Color-Node.html` |
| screen UV, `ComputeScreenPos` | Screen Position | `Screen-Position-Node.html` |
| `SampleSceneDepth`, `_CameraDepthTexture` | Scene Depth | `Scene-Depth-Node.html` |
| `SampleSceneColor`, opaque texture | Scene Color | `Scene-Color-Node.html` |
| `_WorldSpaceCameraPos`, camera props | Camera (Position output) | `Camera-Node.html` |
| `UNITY_MATRIX_V[2].xyz` | **Negate(Camera → Direction)**. The 17.3 docs give `Direction = -UNITY_MATRIX_V[2].xyz`, so a raw `V[2]` points back toward the viewer. | `Camera-Node.html` |
| `unity_ObjectToWorld` position/scale | Object | `Object-Node.html` |
| `GetMainLight()` direction (URP) | "Get Main Light Direction" (doc page `Main-Light-Direction-Node.html`). The 17.3 page doesn't say whether it points toward or away from the light. If the shader also needs light color or shadow attenuation, get all three from one Custom Function instead. | `Main-Light-Direction-Node.html` |
| `GetMainLight(shadowCoord)` color / `shadowAttenuation` | No node. Use a Custom Function (File mode) with a `#ifdef SHADERGRAPH_PREVIEW` fallback. Real shadows also need the `_MAIN_LIGHT_SHADOWS*` keywords on the Blackboard. | `Custom-Function-Node.html` |

## Textures

| HLSL / macro | Node | Doc page |
|---|---|---|
| `tex2D`, `SAMPLE_TEXTURE2D` | Sample Texture 2D | `Sample-Texture-2D-Node.html` |
| `tex2Dlod`, `SAMPLE_TEXTURE2D_LOD` (and any sampling in the vertex stage) | Sample Texture 2D LOD | `Sample-Texture-2D-LOD-Node.html` |
| `texCUBE`, `SAMPLE_TEXTURECUBE` | Sample Cubemap | `Sample-Cubemap-Node.html` |
| `SAMPLE_TEXTURE2D_ARRAY` | Sample Texture 2D Array | `Sample-Texture-2D-Array-Node.html` |
| `SAMPLE_TEXTURE3D` | Sample Texture 3D | `Sample-Texture-3D-Node.html` |
| `UnpackNormal`, `UnpackNormalScale` | Sample Texture 2D with Type = Normal, or Normal Unpack; Normal Strength for scale | `Normal-Unpack-Node.html` / `Normal-Strength-Node.html` |
| blending detail normals | Normal Blend | `Normal-Blend-Node.html` |
| triplanar sampling | Triplanar | `Triplanar-Node.html` |

## Recognizable patterns (prefer the dedicated node)

| Code pattern | Node | Doc page |
|---|---|---|
| `pow(1 - saturate(dot(N, V)), p)` | Fresnel Effect | `Fresnel-Effect-Node.html` |
| `uv * _ST.xy + _ST.zw` | Tiling And Offset | `Tiling-And-Offset-Node.html` |
| rotate UV around a center | Rotate | `Rotate-Node.html` |
| hash/value/gradient noise functions | Simple Noise / Gradient Noise / Voronoi (check the output matches; otherwise Custom Function) | `Simple-Noise-Node.html` / `Gradient-Noise-Node.html` / `Voronoi-Node.html` |
| `Luminance(c)` / `dot(c, float3(0.2126729, 0.7151522, 0.0721750))` | **There is no Luminance node** (`Luminance-Node.html` 404s in 17.3). Use a Dot Product with a Vector 3 holding URP's weights, and reuse that one Vector 3 node everywhere. For a full desaturate, Saturation(0) also works. | `Dot-Product-Node.html` / `Saturation-Node.html` |
| `t = saturate((x - a) / (b - a)); t*t*(3 - 2*t)` | Smoothstep (Edge1 = a, Edge2 = b, In = x). The hand-written form is the same math. | `Smoothstep-Node.html` |
| `flag * (2*u - 1) + 1 - u`, with flag being 0 or 1 | Lerp(One Minus(u), u, flag). It gives the same values and reads better. | `Lerp-Node.html` |
| hue/saturation/contrast adjustments | Hue / Saturation / Contrast | `Hue-Node.html` / `Saturation-Node.html` / `Contrast-Node.html` |
| parallax offset | Parallax Mapping / Parallax Occlusion Mapping | `Parallax-Mapping-Node.html` / `Parallax-Occlusion-Mapping-Node.html` |

## No direct equivalent → Custom Function

Use a Custom Function node (`Custom-Function-Node.html`) for: custom lighting loops, `GetAdditionalLight` iteration, loops with dynamic iteration counts, structs, helper functions that would need dozens of nodes, and noise functions whose output must match exactly. Show the function's inputs and outputs in the diagram and put its HLSL body in the Notes.

## Can't be expressed in Shader Graph

Multi-pass shaders (beyond what the target generates), stencil operations (except through target/renderer features), `GrabPass`, geometry and hull/domain (tessellation) shaders on targets that don't expose them, custom `ZTest` per pass, and compute. List these in Notes.
