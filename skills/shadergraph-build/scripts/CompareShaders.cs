// Renders an original shader and the generated Shader Graph on the same sphere in an isolated
// preview scene (identical material values, one directional light at several angles) and
// reports per-pixel differences. Saves a sheet: original | graph | difference x10.
//
// Config: Temp/sgbuild_compare.txt, one entry per line:
//   original=Assets/.../Original.shader
//   graph=Assets/.../Generated.shadergraph
//   texture _MainTex=Assets/.../albedo.png     (asset path)
//   texture _SdfTex=gradient u                  (procedural: gradient u | gradient v | gradient uv)
//   texture _Mask=rgba 0.8,0,0,0.4              (procedural solid color, linear)
//   float _Strength=0.5
//   color _Tint=1,0.5,0.3,1
//   vector _HeadForward=0,0,1,0                 (also used for properties not in Properties)
// Every property both shaders share starts from the original's defaults.
// Run:    unity command eval_file --file <this> --timeout 120000
// Output: returned text, also written to Temp/sgbuild_compare_result.txt; sheet at Temp/sgbuild_compare.png.
// The first render compiles both shaders' variants and can outlast the CLI's 30 s wait: read the
// result file if the CLI times out.
string origPath = null, graphPath = null;
var cfg = System.IO.File.ReadAllLines("Temp/sgbuild_compare.txt");
foreach (var l in cfg)
{
    if (l.StartsWith("original=")) origPath = l.Substring(9).Trim();
    if (l.StartsWith("graph=")) graphPath = l.Substring(6).Trim();
}
var orig = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Shader>(origPath);
var gen = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Shader>(graphPath);
if (orig == null || gen == null) return "missing shader: original=" + origPath + " graph=" + graphPath;

var temp = new System.Collections.Generic.List<UnityEngine.Object>();
float[] Floats(string s) => System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(s.Split(','), x => float.Parse(x.Trim(), System.Globalization.CultureInfo.InvariantCulture)));
UnityEngine.Texture Procedural(string spec)
{
    var t = new UnityEngine.Texture2D(64, 64, UnityEngine.TextureFormat.RGBA32, false, true) { wrapMode = UnityEngine.TextureWrapMode.Clamp };
    float[] c = spec.StartsWith("rgba") ? Floats(spec.Substring(4)) : null;
    for (int y = 0; y < 64; y++) for (int x = 0; x < 64; x++)
    {
        float u = (x + 0.5f) / 64, v = (y + 0.5f) / 64;
        t.SetPixel(x, y, c != null ? new UnityEngine.Color(c[0], c[1], c[2], c[3])
            : spec == "gradient u" ? new UnityEngine.Color(u, u, u, 1)
            : spec == "gradient v" ? new UnityEngine.Color(v, v, v, 1)
            : new UnityEngine.Color(u, v, 0.5f * (u + v), 1));
    }
    t.Apply(); temp.Add(t); return t;
}

var mo = new UnityEngine.Material(orig); var mg = new UnityEngine.Material(gen); temp.Add(mo); temp.Add(mg);
for (int i = 0; i < orig.GetPropertyCount(); i++)
{
    var n = orig.GetPropertyName(i);
    if (!mg.HasProperty(n)) continue;
    switch (orig.GetPropertyType(i))
    {
        case UnityEngine.Rendering.ShaderPropertyType.Float:
        case UnityEngine.Rendering.ShaderPropertyType.Range: mg.SetFloat(n, mo.GetFloat(n)); break;
        case UnityEngine.Rendering.ShaderPropertyType.Color: mg.SetColor(n, mo.GetColor(n)); break;
        case UnityEngine.Rendering.ShaderPropertyType.Vector: mg.SetVector(n, mo.GetVector(n)); break;
    }
}
foreach (var raw in cfg)
{
    var l = raw.Trim();
    int sp = l.IndexOf(' '), eq = l.IndexOf('=');
    if (sp < 0 || eq < sp) continue;
    var kind = l.Substring(0, sp); var name = l.Substring(sp + 1, eq - sp - 1).Trim(); var val = l.Substring(eq + 1).Trim();
    foreach (var m in new[] { mo, mg })
    {
        if (kind == "texture") m.SetTexture(name, val.StartsWith("Assets/") ? UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Texture>(val) : null);
        if (kind == "float") m.SetFloat(name, Floats(val)[0]);
        if (kind == "color") { var c = Floats(val); m.SetColor(name, new UnityEngine.Color(c[0], c[1], c[2], c.Length > 3 ? c[3] : 1)); }
        if (kind == "vector") { var c = Floats(val); m.SetVector(name, new UnityEngine.Vector4(c[0], c.Length > 1 ? c[1] : 0, c.Length > 2 ? c[2] : 0, c.Length > 3 ? c[3] : 0)); }
    }
    if (kind == "texture" && !val.StartsWith("Assets/")) { var t = Procedural(val); mo.SetTexture(name, t); mg.SetTexture(name, t); }
}

var scene = UnityEditor.SceneManagement.EditorSceneManager.NewPreviewScene();
var sphere = UnityEngine.GameObject.CreatePrimitive(UnityEngine.PrimitiveType.Sphere);
UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(sphere, scene);
var mr = sphere.GetComponent<UnityEngine.MeshRenderer>();
mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
var camGo = new UnityEngine.GameObject("sgbuildCam"); UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(camGo, scene);
var cam = camGo.AddComponent<UnityEngine.Camera>();
cam.scene = scene; cam.transform.position = new UnityEngine.Vector3(0.6f, 0.3f, 2.6f); cam.transform.LookAt(UnityEngine.Vector3.zero);
cam.clearFlags = UnityEngine.CameraClearFlags.SolidColor; cam.backgroundColor = UnityEngine.Color.black; cam.fieldOfView = 30f;
var lightGo = new UnityEngine.GameObject("sgbuildLight"); UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(lightGo, scene);
var light = lightGo.AddComponent<UnityEngine.Light>(); light.type = UnityEngine.LightType.Directional; light.intensity = 1.2f;
light.color = new UnityEngine.Color(1f, 0.95f, 0.9f); light.shadows = UnityEngine.LightShadows.None;

const int W = 160, H = 160;
var rt = new UnityEngine.RenderTexture(W, H, 24, UnityEngine.RenderTextureFormat.ARGBFloat, UnityEngine.RenderTextureReadWrite.Linear);
cam.targetTexture = rt;
UnityEngine.Color[] Render(UnityEngine.Material m)
{
    mr.sharedMaterial = m;
    cam.Render();
    var prev = UnityEngine.RenderTexture.active; UnityEngine.RenderTexture.active = rt;
    var t = new UnityEngine.Texture2D(W, H, UnityEngine.TextureFormat.RGBAFloat, false, true);
    t.ReadPixels(new UnityEngine.Rect(0, 0, W, H), 0, 0); t.Apply();
    UnityEngine.RenderTexture.active = prev;
    var px = t.GetPixels(); UnityEngine.Object.DestroyImmediate(t); return px;
}

var lights = new (string name, UnityEngine.Vector3 euler)[] {
    ("front", new UnityEngine.Vector3(20, 180, 0)), ("left", new UnityEngine.Vector3(15, 100, 0)),
    ("right", new UnityEngine.Vector3(15, 260, 0)), ("back", new UnityEngine.Vector3(25, 10, 0)), ("top", new UnityEngine.Vector3(75, 150, 0)) };
var report = new System.Text.StringBuilder();
var sheet = new UnityEngine.Texture2D(W * 3, H * lights.Length, UnityEngine.TextureFormat.RGBA32, false); temp.Add(sheet);
for (int li = 0; li < lights.Length; li++)
{
    light.transform.rotation = UnityEngine.Quaternion.Euler(lights[li].euler);
    var a = Render(mo); var b = Render(mg);
    double sum = 0; float max = 0, bright = 0; int cover = 0, over1 = 0, over5 = 0;
    for (int i = 0; i < a.Length; i++)
    {
        bool bg = a[i].r + a[i].g + a[i].b < 1e-6f && b[i].r + b[i].g + b[i].b < 1e-6f;
        float d = UnityEngine.Mathf.Max(UnityEngine.Mathf.Abs(a[i].r - b[i].r), UnityEngine.Mathf.Abs(a[i].g - b[i].g), UnityEngine.Mathf.Abs(a[i].b - b[i].b));
        if (!bg) { cover++; sum += d; max = UnityEngine.Mathf.Max(max, d); bright += a[i].grayscale; if (d > 0.01f) over1++; if (d > 0.05f) over5++; }
        int x = i % W, y = i / W, row = (lights.Length - 1 - li) * H;
        sheet.SetPixel(x, row + y, a[i].gamma); sheet.SetPixel(W + x, row + y, b[i].gamma);
        sheet.SetPixel(2 * W + x, row + y, new UnityEngine.Color(d * 10, d * 10, d * 10, 1));
    }
    report.AppendFormat("{0,-6} pixels={1} meanBright={2:F3} meanDiff={3:F5} maxDiff={4:F4} >1%={5} >5%={6}\n",
        lights[li].name, cover, bright / UnityEngine.Mathf.Max(1, cover), sum / UnityEngine.Mathf.Max(1, cover), max, over1, over5);
}
sheet.Apply();
System.IO.File.WriteAllBytes("Temp/sgbuild_compare.png", sheet.EncodeToPNG());
report.Append("sheet: Temp/sgbuild_compare.png (columns: original | graph | difference x10)\n");
System.IO.File.WriteAllText("Temp/sgbuild_compare_result.txt", report.ToString());
cam.targetTexture = null; rt.Release(); temp.Add(rt);
UnityEditor.SceneManagement.EditorSceneManager.ClosePreviewScene(scene);
foreach (var o in temp) UnityEngine.Object.DestroyImmediate(o);
return report.ToString();
