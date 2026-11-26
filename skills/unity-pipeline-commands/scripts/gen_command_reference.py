"""Regenerate references/commands-*.md from a running Editor's command schema.

Usage (from anywhere):
  python -I gen_command_reference.py <unity project path>            # live: GET /api/commands
  python -I gen_command_reference.py --json commands.json            # from a saved schema dump

Reads the port descriptor for port + token (the token is never printed), fetches every command
with full parameter metadata, and writes two files next to this script's ../references/:
  commands-content.md  authoring groups (assets, scenes, GameObjects, prefabs, scripts, animation, materials)
  commands-editor.md   everything else (build, editor, console, settings, packages, runtime, jobs, ...)
"""
import json, os, re, sys, urllib.request
from collections import defaultdict

CONTENT_GROUPS = ("asset", "authoring", "scene", "gameobject", "component", "prefab", "script",
                  "animation", "material")
TYPE_NAMES = {"String": "string", "Int32": "int", "Int64": "long", "Single": "float", "Double": "double",
              "Boolean": "bool", "String[]": "string[]", "Int32[]": "int[]", "Single[]": "float[]"}


def load():
    if sys.argv[1] == "--json":
        return json.load(open(sys.argv[2], encoding="utf-8")), None
    project = sys.argv[1]
    d = json.load(open(os.path.join(project, "Library", "Pipeline", ".unity-pipeline-port"), encoding="utf-8"))
    req = urllib.request.Request(f"http://127.0.0.1:{d['port']}/api/commands?limit=10000",
                                 headers={"Authorization": "Bearer " + d["evalToken"]})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    return data, d.get("unityVersion")


def package_version(project):
    try:
        lock = json.load(open(os.path.join(project, "Packages", "packages-lock.json"), encoding="utf-8"))
        return lock["dependencies"]["com.unity.pipeline"]["version"]
    except Exception:
        return "unknown"


def cell(text):
    return re.sub(r"\s+", " ", (text or "")).replace("|", "\\|").strip()


def fmt_param(p):
    t = TYPE_NAMES.get(p["type"], p["type"])
    s = f"`{p['name']}` {t}"
    if p.get("required"):
        s += " **(req)**"
    elif p.get("defaultValue") not in (None, "", []):
        dv = p["defaultValue"]
        s += f" ={json.dumps(dv) if not isinstance(dv, str) else dv}"
    return s


def write(path, title, intro, groups, version_line):
    lines = [f"# {title}", "", version_line, "", intro, ""]
    for g in sorted(groups):
        lines += [f"## `{g}`", "", "| Command | Parameters | Description |", "|---|---|---|"]
        for c in sorted(groups[g], key=lambda c: c["name"]):
            params = ", ".join(fmt_param(p) for p in c["parameters"]) or "—"
            lines.append(f"| `{c['command']}` | {cell(params)} | {cell(c['description'])} |")
        lines.append("")
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))


data, unity = load()
cmds = data["commands"]
project = sys.argv[1] if sys.argv[1] != "--json" else None
ver = package_version(project) if project else "unknown"
version_line = (f"Generated from the live command schema (`GET /api/commands`) of `com.unity.pipeline` **{ver}**"
                + (f" on Unity {unity}" if unity else "") + f": {len(cmds)} commands. "
                "Regenerate with `scripts/gen_command_reference.py` after a package update; "
                "`unity command <group>` / `GET /api/commands?group=<group>` is the source of truth for the installed version.")
content, editor = defaultdict(list), defaultdict(list)
for c in cmds:
    (content if c["group"].split(".")[0] in CONTENT_GROUPS else editor)[c["group"]].append(c)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")
common = ("Run as `unity command \"<group> <name>\" --param value` (quote the full name with CLI 1.0.0-beta.2), or raw "
          "`POST /api/exec` `{\"command\": \"<group> <name>\", \"parameters\": {...}}`. **(req)** = required; `=x` = default. "
          "ObjectRef = `{\"path\"|\"guid\"+\"fileId\"|\"instanceId\"|\"hierarchyPath\"|\"globalId\": ...}`. "
          "Destructive commands follow the `confirm`/`dry_run` convention (see SKILL.md).")
write(os.path.join(out, "commands-content.md"), "Authoring commands: assets, scenes, GameObjects, prefabs, scripts, animation, materials",
      common, content, version_line)
write(os.path.join(out, "commands-editor.md"), "Editor, build, settings, packages, runtime and job commands",
      common, editor, version_line)
print(f"wrote {sum(map(len, content.values()))} authoring + {sum(map(len, editor.values()))} editor commands to {os.path.normpath(out)}")
