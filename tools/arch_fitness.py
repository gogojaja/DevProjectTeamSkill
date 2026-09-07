#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arch_fitness.py — Architecture Fitness Function Checker (T1)

Industry anchor: BP-01 ThoughtWorks Architecture Fitness Functions
Skill dependency: impl-coach (domain/architecture-to-code.md)

CLI:
  python3 tools/arch_fitness.py run
  python3 tools/arch_fitness.py run --target src/ --incremental --dry-run
"""
import os, sys, re, io, csv, argparse, datetime, subprocess

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORT = os.path.join(ROOT, "台账", "40_架构适配度.csv")

LAYER_RULES = {
    "presentation": {
        "markers": ["controller","router","view","route","presentation","api"],
        "forbidden": {"repository","repository_impl","persistence","dao","data","models"},
    },
    "business": {
        "markers": ["service","usecase","business","domain"],
        "forbidden": {"controller","router","view","route","presentation"},
    },
    "data": {
        "markers": ["repository_impl","persistence","dao","data","models"],
        "forbidden": {"controller","router","view","route","presentation","service","usecase","business"},
    },
}

PY_IMPORT_RE = re.compile(r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)
TS_IMPORT_RE = re.compile(r"""(?:import\s+.*?from\s+['"]([^'"]+)['"])""", re.MULTILINE)

def _detect_layer(filepath):
    p = filepath.lower().replace("\\", "/")
    for layer, cfg in LAYER_RULES.items():
        for m in cfg["markers"]:
            if f"/{m}/" in p or f"/{m}." in p: return layer
    return None

def _extract_imports(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f: content = f.read()
    except: return []
    ext = os.path.splitext(filepath)[1]
    if ext == ".py":
        return [m.group(1) or m.group(2) for m in PY_IMPORT_RE.finditer(content) if m.group(1) or m.group(2)]
    elif ext in (".ts",".tsx",".js",".jsx"):
        return [m.group(1) for m in TS_IMPORT_RE.finditer(content) if m.group(1)]
    return []

def _check_violations(filepath, layer, imports):
    vs = []
    rule = LAYER_RULES.get(layer)
    if not rule: return vs
    for imp in imports:
        il = imp.lower()
        for fb in rule["forbidden"]:
            if fb in il:
                vs.append({"file": filepath, "layer": layer, "import": imp,
                           "violated": fb, "severity": "BLOCK",
                           "fix": f"Remove {layer}'s dependency on {fb}, use interface injection"})
    return vs

def _scan(target, incremental=False):
    files = []
    exts = {".py",".ts",".tsx",".js",".jsx"}
    if incremental:
        try:
            r = subprocess.run(["git","diff","--name-only","HEAD"], cwd=ROOT,
                               capture_output=True, text=True, timeout=10)
            for f in r.stdout.split("\n"):
                fp = os.path.join(ROOT, f.strip()) if f.strip() else ""
                if fp and os.path.isfile(fp) and os.path.splitext(f)[1] in exts: files.append(fp)
            return files
        except: pass
    for dp, dns, fns in os.walk(target):
        dns[:] = [d for d in dns if not d.startswith(".") and d not in ("node_modules","__pycache__",".venv","venv")]
        for fn in fns:
            if os.path.splitext(fn)[1] in exts: files.append(os.path.join(dp, fn))
    return files

def run(args):
    target = os.path.join(ROOT, args.target) if args.target else os.path.join(ROOT, "src")
    if not os.path.isdir(target): target = ROOT
    files = _scan(target, args.incremental)
    violations = []
    for fp in files:
        rel = os.path.relpath(fp, ROOT)
        layer = _detect_layer(rel)
        if not layer: continue
        imports = _extract_imports(fp)
        violations.extend(_check_violations(rel, layer, imports))

    blocking = [v for v in violations if v["severity"] == "BLOCK"]
    if args.dry_run:
        print(f"[arch-fitness] dry-run: {len(files)} files, {len(violations)} violations ({len(blocking)} blocking)")
        for v in violations[:20]:
            print(f"  [{v['severity']}] {v['file']} (layer={v['layer']}) -> {v['import']} (violates: {v['violated']})")
        return 0

    if violations:
        header = ["Time","File","Layer","Import","Violated Layer","Severity","Fix"]
        new = not os.path.exists(REPORT)
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with io.open(REPORT, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(header)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for v in violations:
                w.writerow([now, v["file"], v["layer"], v["import"], v["violated"], v["severity"], v["fix"]])

    status = "FAIL" if blocking else "PASS"
    print(f"[arch-fitness] {len(files)} files, {len(violations)} violations ({len(blocking)} blocking), decision={status}")
    return 1 if blocking else 0

def main():
    ap = argparse.ArgumentParser(description="Architecture Fitness Checker (T1)")
    sub = ap.add_subparsers(dest="command")
    r = sub.add_parser("run")
    r.add_argument("--target", default="")
    r.add_argument("--incremental", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.command == "run": sys.exit(run(args))
    ap.print_help()

if __name__ == "__main__":
    main()
