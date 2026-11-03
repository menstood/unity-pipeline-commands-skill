// Dumps every Shader Graph node type of the installed version: title, class, default
// serialized JSON, slots (id, name, direction, slot class, JSON) and each UI setting with the
// node JSON produced for every allowed value. Run with: unity command eval_file --file <this>
var asm = System.Type.GetType("UnityEditor.ShaderGraph.AbstractMaterialNode, Unity.ShaderGraph.Editor").Assembly;
var baseT = asm.GetType("UnityEditor.ShaderGraph.AbstractMaterialNode");
var titleT = asm.GetType("UnityEditor.ShaderGraph.TitleAttribute");
var slotT = asm.GetType("UnityEditor.ShaderGraph.MaterialSlot");
var ctrlT = asm.GetType("UnityEditor.ShaderGraph.Drawing.Controls.IControlAttribute");
var BF = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
string Q(string s) => s == null ? "null" : "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "") + "\"";
int Ver(object o) { var p = o.GetType().GetProperty("sgVersion", BF); return p == null ? 0 : (int)p.GetValue(o); }
var sb = new System.Text.StringBuilder("[");
int count = 0, failed = 0;
foreach (var t in asm.GetTypes())
{
    if (t.IsAbstract || !baseT.IsAssignableFrom(t)) continue;
    var ta = t.GetCustomAttributes(titleT, false);
    if (ta.Length == 0) continue;
    object node;
    try { node = System.Activator.CreateInstance(t, true); } catch { failed++; continue; }
    var title = (string[])titleT.GetField("title").GetValue(ta[0]);
    if (count++ > 0) sb.Append(",");
    sb.Append("{\"title\":").Append(Q(title[title.Length - 1])).Append(",\"path\":").Append(Q(string.Join("/", title)))
      .Append(",\"type\":").Append(Q(t.FullName)).Append(",\"sgVersion\":").Append(Ver(node))
      .Append(",\"json\":").Append(UnityEngine.JsonUtility.ToJson(node)).Append(",\"slots\":[");
    var list = (System.Collections.IList)System.Activator.CreateInstance(typeof(System.Collections.Generic.List<>).MakeGenericType(slotT));
    baseT.GetMethod("GetSlots").MakeGenericMethod(slotT).Invoke(node, new object[] { list });
    int si = 0;
    foreach (var s in list)
    {
        if (si++ > 0) sb.Append(",");
        sb.Append("{\"id\":").Append(slotT.GetProperty("id").GetValue(s))
          .Append(",\"name\":").Append(Q((string)slotT.GetMethod("RawDisplayName").Invoke(s, null)))
          .Append(",\"input\":").Append(((bool)slotT.GetProperty("isInputSlot").GetValue(s)) ? "true" : "false")
          .Append(",\"type\":").Append(Q(s.GetType().FullName)).Append(",\"sgVersion\":").Append(Ver(s))
          .Append(",\"json\":").Append(UnityEngine.JsonUtility.ToJson(s)).Append("}");
    }
    sb.Append("],\"settings\":[");
    int pi = 0;
    foreach (var p in t.GetProperties(BF))
    {
        var ca = System.Linq.Enumerable.FirstOrDefault(p.GetCustomAttributes(true), a => ctrlT.IsAssignableFrom(a.GetType()));
        if (ca == null || !p.CanWrite) continue;
        var lf = ca.GetType().GetField("m_Label", BF);
        var label = (lf != null ? (string)lf.GetValue(ca) : null) ?? p.Name;
        var pt = p.PropertyType;
        object[] values = pt.IsEnum ? System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Cast<object>(System.Enum.GetValues(pt)))
                        : pt == typeof(bool) ? new object[] { false, true }
                        : pt == typeof(string) ? new object[] { "xyz", "xz", "x" }
                        : new object[0];
        object orig; try { orig = p.GetValue(node); } catch { continue; }
        if (pi++ > 0) sb.Append(",");
        sb.Append("{\"label\":").Append(Q(label)).Append(",\"property\":").Append(Q(p.Name)).Append(",\"ptype\":").Append(Q(pt.FullName)).Append(",\"values\":[");
        int vi = 0;
        foreach (var v in values)
        {
            string js;
            try { p.SetValue(node, v); js = UnityEngine.JsonUtility.ToJson(node); } catch { continue; }
            if (vi++ > 0) sb.Append(",");
            sb.Append("{\"value\":").Append(Q(v.ToString())).Append(",\"json\":").Append(js).Append("}");
        }
        try { p.SetValue(node, orig); } catch { }
        sb.Append("]}");
    }
    sb.Append("]}");
}
sb.Append("]");
System.IO.File.WriteAllText("Temp/sg_catalog.json", sb.ToString());
return count + " nodes, " + failed + " failed to construct, " + sb.Length + " chars";
