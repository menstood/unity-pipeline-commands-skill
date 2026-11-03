// Imports a generated .shadergraph and checks it the way Shader Graph itself sees it:
// shader compile messages, nodes/edges that survived loading, nodes with errors.
// Also writes Shader Graph's generated HLSL so it can be grepped.
// Config: Temp/sgbuild_check.txt with one line `graph=Assets/.../Name.shadergraph`
// Run:    unity command eval_file --file <this> --timeout 60000
// Output: returned text, also written to Temp/sgbuild_check_result.txt (survives a CLI timeout).
string graphPath = null;
foreach (var line in System.IO.File.ReadAllLines("Temp/sgbuild_check.txt"))
    if (line.StartsWith("graph=")) graphPath = line.Substring(6).Trim();
if (graphPath == null) return "Temp/sgbuild_check.txt needs a graph=<asset path> line";

var sb = new System.Text.StringBuilder();
UnityEditor.AssetDatabase.ImportAsset(graphPath, UnityEditor.ImportAssetOptions.ForceUpdate);
var sh = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Shader>(graphPath);
if (sh == null) return "import failed: no shader at " + graphPath;
sb.Append("shader: " + sh.name + " supported=" + sh.isSupported + " messages=" + UnityEditor.ShaderUtil.GetShaderMessageCount(sh) + "\n");
foreach (var m in UnityEditor.ShaderUtil.GetShaderMessages(sh)) sb.Append("  " + m.severity + ": " + m.message + " (line " + m.line + ")\n");

// Load through Shader Graph's own importer (internal API, reached by reflection).
var asm = System.Type.GetType("UnityEditor.ShaderGraph.ShaderGraphImporter, Unity.ShaderGraph.Editor").Assembly;
var BF = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var imp = asm.GetType("UnityEditor.ShaderGraph.ShaderGraphImporter");
var getText = System.Linq.Enumerable.First(imp.GetMethods(System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static),
    x => x.Name == "GetShaderText" && x.GetParameters().Length == 4);
var args = new object[] { graphPath, null, System.Activator.CreateInstance(asm.GetType("UnityEditor.ShaderGraph.AssetCollection"), true), null };
var code = (string)getText.Invoke(null, args);
var genPath = "Temp/" + System.IO.Path.GetFileNameWithoutExtension(graphPath) + ".generated.shader";
System.IO.File.WriteAllText(genPath, code);

var graph = args[3];
var gdT = graph.GetType();
var edges = (System.Collections.ICollection)gdT.GetProperty("edges", BF).GetValue(graph);
var nodes = (System.Collections.IEnumerable)gdT.GetMethod("GetNodes", BF)
    .MakeGenericMethod(asm.GetType("UnityEditor.ShaderGraph.AbstractMaterialNode")).Invoke(graph, null);
int n = 0, bad = 0;
var badNames = new System.Text.StringBuilder();
foreach (var node in nodes)
{
    n++;
    if ((bool)node.GetType().GetProperty("hasError", BF).GetValue(node)) { bad++; badNames.Append(" " + node.GetType().Name); }
}
sb.Append("loaded: nodes=" + n + " edges=" + edges.Count + " nodesWithError=" + bad + badNames + "\n");
sb.Append("generated HLSL: " + genPath + " (" + code.Length + " chars)\n");

var props = new System.Text.StringBuilder();
for (int i = 0; i < sh.GetPropertyCount(); i++)
{
    var name = sh.GetPropertyName(i);
    if (name.StartsWith("unity_") || name.StartsWith("_Queue")) continue;
    props.Append("  " + name + " \"" + sh.GetPropertyDescription(i) + "\" " + sh.GetPropertyType(i)
        + ((((int)sh.GetPropertyFlags(i)) & 1) != 0 ? " [hidden]" : "") + "\n");
}
sb.Append("properties:\n").Append(props);
System.IO.File.WriteAllText("Temp/sgbuild_check_result.txt", sb.ToString());
return sb.ToString();
