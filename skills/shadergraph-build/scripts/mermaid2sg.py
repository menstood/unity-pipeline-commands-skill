"""mermaid2sg: convert shader-teardown Mermaid diagrams into a Shader Graph (.shadergraph).

Inputs
  --md        teardown markdown (every ```mermaid block is read; diagrams are stitched
              together through [["NAME"]] reference boxes)
  --catalog   sg_catalog.json dumped from the running Editor (SgCatalog.cs): node classes,
              slot ids/names and setting -> serialized-field patches for the installed version
  --samples   Shader Graph package root (property / PropertyNode / target / block templates)
  --shader    optional original .shader: property display names, defaults and Range sliders
  --hlsl      optional Custom Function file (port types are read from `void Name_float(...)`)
  --hlsl-guid asset GUID of that file inside the Unity project
  --out       output .shadergraph

Fails loudly on any node, port or setting it can't map. Never guesses.
"""
import argparse, copy, glob, json, os, re, sys, uuid
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("--md", required=True)
ap.add_argument("--catalog", required=True)
ap.add_argument("--samples", required=True)
ap.add_argument("--shader")
ap.add_argument("--hlsl")
ap.add_argument("--hlsl-guid")
ap.add_argument("--out", required=True)
ap.add_argument("--render-face", default="Front", choices=["Both", "Back", "Front"])
ap.add_argument("--names", help="JSON {reference: display name}; overrides display names from --shader (e.g. translations)")
args = ap.parse_args()

ERRORS = []


def fail(msg):
    ERRORS.append(msg)


def nid():
    return uuid.uuid4().hex


# ---------------------------------------------------------------- catalog + samples
CATALOG = defaultdict(list)
for n in json.load(open(args.catalog, encoding="utf-8")):
    CATALOG[n["title"]].append(n)


def parse_multijson(path):
    s = open(path, encoding="utf-8").read()
    dec, i, out = json.JSONDecoder(), 0, []
    while True:
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s):
            return out
        o, i = dec.raw_decode(s, i)
        out.append(o)


SAMPLES = []
for f in sorted(glob.glob(os.path.join(args.samples, "**", "*.shadergraph"), recursive=True)):
    try:
        SAMPLES.append(parse_multijson(f))
    except Exception:
        pass


def sample_obj(mtype, pred=lambda o: True):
    for objs in SAMPLES:
        for o in objs:
            if o["m_Type"] == mtype and pred(o):
                return copy.deepcopy(o)
    raise SystemExit(f"no sample template for {mtype}")


def sample_bundle(mtype, pred):
    for objs in SAMPLES:
        by_id = {o["m_ObjectId"]: o for o in objs}
        for o in objs:
            if o["m_Type"] == mtype and pred(o, by_id):
                slots = [by_id.get(s["m_Id"]) for s in o.get("m_Slots", [])]
                if all(slots):
                    return copy.deepcopy(o), copy.deepcopy(slots)
    raise SystemExit(f"no sample template for {mtype}")


SLOT_TEMPLATES = {}
for entries in CATALOG.values():
    for n in entries:
        for s in n["slots"]:
            SLOT_TEMPLATES.setdefault((s["type"].split(".")[-1], s["input"]), s["json"])

# ---------------------------------------------------------------- original shader properties
SHADER_PROPS = {}
if args.shader:
    src = open(args.shader, encoding="utf-8").read()
    block = src[src.index("Properties"):src.index("SubShader")]
    pat = re.compile(r'(?:\[[^\]]*\]\s*)*(_\w+)\s*\(\s*"([^"]*)"\s*,\s*([^)]*\)?)\s*\)\s*=\s*([^\n{]+)')
    for m in pat.finditer(block):
        ref, disp, ptype, val = m.group(1), m.group(2), m.group(3).strip(), m.group(4).strip()
        SHADER_PROPS[ref] = {"display": disp, "type": ptype, "value": val.strip().strip('"')}

DISPLAY_NAMES = json.load(open(args.names, encoding="utf-8")) if args.names else {}

# ---------------------------------------------------------------- custom function signatures
CF_SIGS = {}
if args.hlsl:
    code = open(args.hlsl, encoding="utf-8").read()
    for m in re.finditer(r"void\s+(\w+?)_float\s*\(([^)]*)\)", code):
        params = []
        for p in m.group(2).split(","):
            toks = p.split()
            out = toks[0] == "out"
            if out:
                toks = toks[1:]
            params.append({"type": toks[0], "name": toks[1], "out": out})
        CF_SIGS[m.group(1)] = params

# ---------------------------------------------------------------- parse Mermaid
NODE_RE = re.compile(r'^(\w+)(\[\[|\(\[|\[/|\{\{|\[)"(.*)"(\]\]|\]\)|/\]|\}\}|\])$')
EDGE_RE = re.compile(r'^(\w+)\s*-->\s*(?:\|"(.*?)"\|\s*)?(\w+)$')
SHAPE = {"[[": "ref", "([": "block", "[/": "prop", "{{": "cf", "[": "node"}

md = open(args.md, encoding="utf-8").read()
diagrams = re.findall(r"```mermaid\n(.*?)```", md, re.S)
if not diagrams:
    raise SystemExit("no ```mermaid blocks found")

DNODES, DEDGES = {}, []  # key = (diagram index, id)
for di, text in enumerate(diagrams):
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%") or line.startswith("flowchart") or line.startswith("subgraph") or line == "end":
            continue
        m = NODE_RE.match(line)
        if m:
            DNODES[(di, m.group(1))] = {"kind": SHAPE[m.group(2)], "label": m.group(3), "diagram": di, "id": m.group(1)}
            continue
        m = EDGE_RE.match(line)
        if m:
            DEDGES.append(((di, m.group(1)), m.group(2) or "", (di, m.group(3))))
            continue
        fail(f"diagram {di + 1}: can't parse line: {line}")

for a, _, b in DEDGES:
    for k in (a, b):
        if k not in DNODES:
            fail(f"diagram {k[0] + 1}: edge uses undeclared node '{k[1]}'")


def ref_name(label):
    m = re.match(r"[A-Z0-9_]+", label)
    return m.group(0) if m else label


def split_label(label):
    """'Out → A (.xyz)' -> ('Out', 'A');  '→ B' -> ('', 'B');  'Direction' -> ('Direction', '')"""
    label = re.sub(r"\s*\([^)]*\)\s*$", "", label).strip()
    if "→" in label:
        a, b = label.split("→", 1)
        return a.strip(), b.strip()
    return label, ""


# ---------------------------------------------------------------- graph objects
objects, nodes, edges, properties = [], [], [], {}
GNODE = {}  # (di, id) -> {"node": json, "slots": {name_lower: (id, input)}, ...}
T = "UnityEditor.ShaderGraph."
COORD = {"object": 0, "view": 1, "world": 2, "tangent": 3, "absoluteworld": 4, "screen": 5}


def norm(s):
    return re.sub(r"[\s_:]", "", s).lower()


def parse_floats(text):
    try:
        return [float(x) for x in re.split(r"[,\s]+", text.strip().strip("()")) if x]
    except ValueError:
        return None


def set_slot_value(slot, vals):
    v = slot.get("m_Value")
    if isinstance(v, dict) and "e00" in v:
        for k in v:
            v[k] = float(vals[0]) if len(vals) == 1 else 0.0
        if len(vals) > 1:
            for i, x in enumerate(vals):
                v[f"e0{i}"] = x
    elif isinstance(v, dict):
        keys = [k for k in ("x", "y", "z", "w", "r", "g", "b", "a") if k in v]
        if len(vals) == 1:
            for k in keys:
                v[k] = float(vals[0])
        else:
            for k, x in zip(keys, vals):
                v[k] = float(x)
    elif isinstance(v, (int, float)):
        slot["m_Value"] = float(vals[0])
    else:
        return False
    return True


def make_node(entry, key, x=0.0, y=0.0):
    node = copy.deepcopy(entry["json"])
    node["m_ObjectId"] = nid()
    node["m_Group"] = {"m_Id": ""}
    node.setdefault("m_DrawState", {"m_Expanded": True, "m_Position": {"serializedVersion": "2", "x": 0, "y": 0, "width": 0, "height": 0}})
    node["m_Slots"] = []
    slots = {}
    for s in entry["slots"]:
        sj = copy.deepcopy(s["json"])
        sj["m_ObjectId"] = nid()
        node["m_Slots"].append({"m_Id": sj["m_ObjectId"]})
        slots[norm(s["name"])] = {"id": s["id"], "input": s["input"], "json": sj}
        objects.append(sj)
    objects.append(node)
    nodes.append(node)
    GNODE[key] = {"node": node, "slots": slots, "entry": entry}
    return GNODE[key]


def apply_settings(g, parts, key):
    entry, node = g["entry"], g["node"]
    title = entry["title"]
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "→" in part and ":" not in part and title == "Transform":
            a, b = (norm(x) for x in part.split("→"))
            node["m_Conversion"] = {"from": COORD[a], "to": COORD[b]}
            continue
        if ":" not in part:
            vals = parse_floats(part)
            inputs = [s for s in g["slots"].values() if s["input"]]
            if vals and title.startswith("Vector") and len(vals) == len(inputs):
                for s, v in zip(sorted(inputs, key=lambda s: s["id"]), vals):
                    set_slot_value(s["json"], [v])
                continue
            fail(f"{key}: can't read setting '{part}' on {title}")
            continue
        k, v = (x.strip() for x in part.split(":", 1))
        nk = norm(k)
        slot = g["slots"].get(nk)
        if slot and slot["input"]:
            vals = parse_floats(v)
            if vals is None or not set_slot_value(slot["json"], vals):
                fail(f"{key}: bad default '{part}' for port {k} on {title}")
            continue
        if nk == "space" and "m_Space" in node:
            node["m_Space"] = COORD[norm(v)]
            continue
        if nk == "normalizeoutput" and "m_Normalize" in node:
            node["m_Normalize"] = v.lower() in ("on", "true", "yes", "1")
            continue
        if nk == "mask" and "_maskInput" in node:
            node["_maskInput"] = v
            node["convertedMask"] = ""
            continue
        setting = next((s for s in entry["settings"] if norm(s["label"]) == nk), None)
        if setting:
            val = next((x for x in setting["values"] if norm(x["value"]) == norm(v)), None)
            if not val:
                fail(f"{key}: {title} setting {k} has no value '{v}' (allowed: {[x['value'] for x in setting['values']]})")
                continue
            for fk, fv in val["json"].items():
                if fk not in ("m_ObjectId", "m_Slots", "m_DrawState", "m_Group") and entry["json"].get(fk) != fv:
                    node[fk] = fv
            continue
        fail(f"{key}: unknown setting '{k}' on {title}")


PROP_TYPES = {
    "texture2d": T + "Internal.Texture2DShaderProperty",
    "color": T + "Internal.ColorShaderProperty",
    "float": T + "Internal.Vector1ShaderProperty",
    "vector2": T + "Internal.Vector2ShaderProperty",
    "vector3": T + "Internal.Vector3ShaderProperty",
    "vector4": T + "Internal.Vector4ShaderProperty",
}
TEX_DEFAULT = {"white": 0, "black": 1, "grey": 2, "gray": 2, "bump": 3, "lineargrey": 4, "red": 5}


def get_property(label, key):
    # "_Ref : Type", optional "= (1,2,3)", optional flags "hidden", "normal"
    m = re.match(r"(_\w+)\s*:\s*(\w+)(.*)$", label)
    if not m:
        fail(f"{key}: bad property label '{label}'")
        return None
    ref, ptype, rest = m.group(1), m.group(2).lower(), m.group(3)
    if ref in properties:
        return properties[ref]
    if ptype not in PROP_TYPES:
        fail(f"{key}: unsupported property type {ptype}")
        return None
    p = sample_obj(PROP_TYPES[ptype])
    src = SHADER_PROPS.get(ref, {})
    display = DISPLAY_NAMES.get(ref) or src.get("display") or ref.lstrip("_")
    p.update({"m_ObjectId": nid(), "m_Guid": {"m_GuidSerialized": str(uuid.uuid4())}, "m_Name": display,
              "m_RefNameGeneratedByDisplayName": display, "m_DefaultReferenceName": ref, "m_OverrideReferenceName": ref,
              # "hidden" = exposed but [HideInInspector]: the material still stores the value and
              # scripts / MaterialPropertyBlocks can set it. Un-exposed properties can't be saved.
              "m_GeneratePropertyBlock": True, "m_Hidden": "hidden" in rest})
    dm = re.search(r"=\s*\(([^)]*)\)|=\s*([-\d.eE]+)", rest)
    default = parse_floats(dm.group(1) or dm.group(2)) if dm else None
    sval = src.get("value", "")
    if ptype == "texture2d":
        p["isMainTexture"] = ref == "_MainTex"
        p["useTilingAndOffset"] = False
        kind = "bump" if "normal" in rest else (sval.split("{")[0].strip().strip('"') or "white")
        p["m_DefaultType"] = TEX_DEFAULT.get(kind.lower(), 0)
        p["m_Value"] = {"m_SerializedTexture": "", "m_Guid": ""}
    elif ptype == "color":
        vals = default or parse_floats(sval) or [1, 1, 1, 1]
        vals = (vals + [1.0])[:4] if len(vals) == 3 else vals
        p["m_Value"] = dict(zip("rgba", vals))
    elif ptype == "float":
        p["m_Value"] = (default or parse_floats(sval) or [0.0])[0]
        rng = re.match(r"Range\s*\(\s*([-\d.]+)\s*,\s*([-\d.]+)", src.get("type", ""))
        if rng:
            p["m_FloatType"] = 1
            p["m_RangeValues"] = {"x": float(rng.group(1)), "y": float(rng.group(2))}
        else:
            p["m_FloatType"] = 0
    else:
        vals = default or parse_floats(sval) or [0, 0, 0, 0]
        p["m_Value"] = dict(zip("xyzw", (vals + [0, 0, 0, 0])[:4]))
    objects.append(p)
    properties[ref] = p
    return p


def make_property_node(prop, key):
    def pred(o, by_id):
        r = by_id.get(o.get("m_Property", {}).get("m_Id"))
        return r is not None and r["m_Type"] == prop["m_Type"]
    node, slots = sample_bundle(T + "PropertyNode", pred)
    node["m_ObjectId"] = nid()
    node["m_Group"] = {"m_Id": ""}
    node["m_Property"] = {"m_Id": prop["m_ObjectId"]}
    node["m_Slots"] = []
    for s in slots:
        s["m_ObjectId"] = nid()
        s["m_DisplayName"] = prop["m_Name"]
        node["m_Slots"].append({"m_Id": s["m_ObjectId"]})
        objects.append(s)
    objects.append(node)
    nodes.append(node)
    GNODE[key] = {"node": node, "slots": {"out": {"id": 0, "input": False, "json": slots[0]}}, "entry": None, "prop": True}


CF_SLOT = {"float": "Vector1MaterialSlot", "float2": "Vector2MaterialSlot", "float3": "Vector3MaterialSlot", "float4": "Vector4MaterialSlot"}


def make_custom_function(name, key):
    if name not in CF_SIGS:
        fail(f"diagram {key[0] + 1} {key[1]}: Custom Function {name} not found in --hlsl (looked for void {name}_float(...))")
        return
    if not args.hlsl_guid:
        fail("--hlsl-guid is required for Custom Function nodes")
        return
    entry = CATALOG["Custom Function"][0]
    g = make_node(entry, key)
    node = g["node"]
    node.update({"m_SourceType": 0, "m_FunctionName": name, "m_FunctionSource": args.hlsl_guid, "m_FunctionBody": ""})
    for i, p in enumerate(CF_SIGS[name]):
        cls = CF_SLOT.get(p["type"])
        if not cls:
            fail(f"{key}: unsupported Custom Function port type {p['type']}")
            continue
        sj = copy.deepcopy(SLOT_TEMPLATES[(cls, not p["out"])])
        sj.update({"m_ObjectId": nid(), "m_Id": i, "m_DisplayName": p["name"], "m_ShaderOutputName": p["name"],
                   "m_SlotType": 1 if p["out"] else 0})
        if isinstance(sj.get("m_Value"), dict):
            sj["m_Value"] = {k: 0.0 for k in sj["m_Value"]}
            sj["m_DefaultValue"] = {k: 0.0 for k in sj["m_DefaultValue"]}
        else:
            sj["m_Value"] = sj["m_DefaultValue"] = 0.0
        node["m_Slots"].append({"m_Id": sj["m_ObjectId"]})
        g["slots"][norm(p["name"])] = {"id": i, "input": not p["out"], "json": sj}
        objects.append(sj)


BLOCKS = {}


def get_block(label, key):
    name = norm(label.split("=")[0])
    desc = {"basecolor": "SurfaceDescription.BaseColor", "alpha": "SurfaceDescription.Alpha",
            "alphaclipthreshold": "SurfaceDescription.AlphaClipThreshold", "emission": "SurfaceDescription.Emission"}.get(name)
    if not desc:
        fail(f"{key}: unknown Master Stack block '{label}'")
        return None
    if desc not in BLOCKS:
        node, slots = sample_bundle(T + "BlockNode", lambda o, _: o.get("m_Name") == desc)
        node["m_ObjectId"] = nid()
        node["m_Slots"] = []
        for s in slots:
            s["m_ObjectId"] = nid()
            node["m_Slots"].append({"m_Id": s["m_ObjectId"]})
            objects.append(s)
        objects.append(node)
        nodes.append(node)
        BLOCKS[desc] = node
    return BLOCKS[desc]


# create graph nodes for every diagram node
for key, d in DNODES.items():
    kind, label = d["kind"], d["label"]
    if kind == "node":
        lines = label.split("<br/>")
        title = lines[0].strip()
        entries = CATALOG.get(title)
        if not entries:
            fail(f"diagram {key[0] + 1}: '{key[1]}' uses unknown node '{title}'")
            continue
        g = make_node(entries[0], key)
        apply_settings(g, [p for ln in lines[1:] for p in ln.split("·")], f"diagram {key[0] + 1} {key[1]}")
    elif kind == "prop":
        p = get_property(label, f"diagram {key[0] + 1} {key[1]}")
        if p:
            make_property_node(p, key)
    elif kind == "cf":
        m = re.match(r"Custom Function:\s*(\w+)", label)
        if m:
            make_custom_function(m.group(1), key)
        else:
            fail(f"{key}: bad Custom Function label")
    elif kind == "block":
        b = get_block(label, f"diagram {key[0] + 1} {key[1]}")
        if b:
            GNODE[key] = {"node": b, "slots": {}, "entry": None, "block": True}

# standard Unlit vertex blocks + required fragment blocks
for desc in ("VertexDescription.Position", "VertexDescription.Normal", "VertexDescription.Tangent"):
    node, slots = sample_bundle(T + "BlockNode", lambda o, _, d=desc: o.get("m_Name") == d)
    node["m_ObjectId"] = nid()
    node["m_Slots"] = []
    for s in slots:
        s["m_ObjectId"] = nid()
        node["m_Slots"].append({"m_Id": s["m_ObjectId"]})
        objects.append(s)
    objects.append(node)
    nodes.append(node)
    BLOCKS[desc] = node
for label in ("Base Color", "Alpha"):
    get_block(label, "default blocks")


# ---------------------------------------------------------------- resolve edges
def out_slot(key, port):
    g = GNODE.get(key)
    if g is None:
        fail(f"diagram {key[0] + 1}: edge from '{key[1]}', which produced no graph node")
        return None
    if g.get("prop"):
        return 0
    outs = {k: s for k, s in g["slots"].items() if not s["input"]}
    if port:
        s = outs.get(norm(port))
        if s is None:
            fail(f"diagram {key[0] + 1}: {key[1]} has no output port '{port}' (has {list(outs)})")
            return None
        return s["id"]
    if len(outs) == 1:
        return next(iter(outs.values()))["id"]
    fail(f"diagram {key[0] + 1}: edge from {key[1]} needs an output port name (has {list(outs)})")
    return None


def in_slot(key, port):
    g = GNODE.get(key)
    if g is None:
        fail(f"diagram {key[0] + 1}: edge into '{key[1]}', which produced no graph node")
        return None
    if g.get("block"):
        return 0
    ins = {k: s for k, s in g["slots"].items() if s["input"]}
    s = ins.get(norm(port))
    if s is None:
        fail(f"diagram {key[0] + 1}: {key[1]} has no input port '{port}' (has {list(ins)})")
        return None
    return s["id"]


REFS = {}
for a, label, b in DEDGES:  # ref definitions: <node> --> o_NAME
    if DNODES.get(b, {}).get("kind") == "ref":
        out_port, _ = split_label(label)
        name = ref_name(DNODES[b]["label"])
        if name in REFS:
            fail(f"reference {name} defined twice")
        REFS[name] = (a, out_slot(a, out_port))

used_inputs = set()
for a, label, b in DEDGES:
    if DNODES.get(b, {}).get("kind") == "ref":
        continue
    out_port, in_port = split_label(label)
    if DNODES.get(a, {}).get("kind") == "ref":
        name = ref_name(DNODES[a]["label"])
        if name not in REFS:
            fail(f"diagram {a[0] + 1}: reference {name} is used but never defined")
            continue
        src_key, src_slot = REFS[name]
    else:
        src_key, src_slot = a, out_slot(a, out_port)
    dst_slot = in_slot(b, in_port)
    if src_slot is None or dst_slot is None or src_key not in GNODE:
        continue
    dst_id = GNODE[b]["node"]["m_ObjectId"]
    if (dst_id, dst_slot) in used_inputs:
        fail(f"diagram {b[0] + 1}: input {in_port} of {b[1]} is connected twice")
        continue
    used_inputs.add((dst_id, dst_slot))
    edges.append({"m_OutputSlot": {"m_Node": {"m_Id": GNODE[src_key]["node"]["m_ObjectId"]}, "m_SlotId": src_slot},
                  "m_InputSlot": {"m_Node": {"m_Id": dst_id}, "m_SlotId": dst_slot}})

if ERRORS:
    print(f"FAILED with {len(ERRORS)} problem(s):", file=sys.stderr)
    for e in ERRORS:
        print("  -", e, file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------- layout: columns by distance to the output
by_id = {n["m_ObjectId"]: n for n in nodes}
succ = defaultdict(set)
for e in edges:
    succ[e["m_OutputSlot"]["m_Node"]["m_Id"]].add(e["m_InputSlot"]["m_Node"]["m_Id"])
depth = {}


def dist(n, seen=()):
    if n in depth:
        return depth[n]
    if n in seen:
        return 0
    d = 1 + max((dist(s, seen + (n,)) for s in succ[n]), default=-1)
    depth[n] = d
    return d


block_ids = {b["m_ObjectId"] for b in BLOCKS.values()}
columns = defaultdict(list)
for n in nodes:
    if n["m_ObjectId"] in block_ids:
        continue
    columns[dist(n["m_ObjectId"])].append(n)
for d, col in columns.items():
    y = 0.0
    for n in col:
        n["m_DrawState"]["m_Position"].update({"x": -320.0 * d - 100.0, "y": y})
        y += 60.0 + 26.0 * len(n.get("m_Slots", []))

# ---------------------------------------------------------------- target + graph
sub = sample_obj("UnityEditor.Rendering.Universal.ShaderGraph.UniversalUnlitSubTarget")
sub["m_ObjectId"] = nid()
tgt = sample_obj("UnityEditor.Rendering.Universal.ShaderGraph.UniversalTarget")
tgt.update({"m_ObjectId": nid(), "m_ActiveSubTarget": {"m_Id": sub["m_ObjectId"]}, "m_SurfaceType": 0,
            "m_RenderFace": {"Both": 0, "Back": 1, "Front": 2}[args.render_face], "m_AlphaClip": False})
cat = sample_obj(T + "CategoryData")
cat.update({"m_ObjectId": nid(), "m_Name": "", "m_ChildObjectList": [{"m_Id": p["m_ObjectId"]} for p in properties.values()]})
objects += [sub, tgt, cat]

graph = sample_obj(T + "GraphData")
graph.update({
    "m_ObjectId": nid(),
    "m_Properties": [{"m_Id": p["m_ObjectId"]} for p in properties.values()],
    "m_Keywords": [], "m_Dropdowns": [],
    "m_CategoryData": [{"m_Id": cat["m_ObjectId"]}],
    "m_Nodes": [{"m_Id": n["m_ObjectId"]} for n in nodes],
    "m_GroupDatas": [], "m_StickyNoteDatas": [],
    "m_Edges": edges,
    "m_VertexContext": {"m_Position": {"x": 0.0, "y": 0.0}, "m_Blocks": [{"m_Id": BLOCKS[d]["m_ObjectId"]} for d in
                        ("VertexDescription.Position", "VertexDescription.Normal", "VertexDescription.Tangent")]},
    "m_FragmentContext": {"m_Position": {"x": 0.0, "y": 200.0}, "m_Blocks": [{"m_Id": BLOCKS[d]["m_ObjectId"]} for d in BLOCKS
                          if d.startswith("SurfaceDescription")]},
    "m_Path": "Shader Graphs",
    "m_OutputNode": {"m_Id": ""},
    "m_SubDatas": [],
    "m_ActiveTargets": [{"m_Id": tgt["m_ObjectId"]}],
})

with open(args.out, "w", encoding="utf-8", newline="\n") as f:
    for o in [graph] + objects:
        f.write(json.dumps(o, indent=4))
        f.write("\n\n")
print(f"wrote {args.out}: {len(diagrams)} diagram(s), {len(nodes)} nodes ({len(BLOCKS)} blocks), "
      f"{len(edges)} edges, {len(properties)} properties, {len(REFS)} cross-diagram refs")
