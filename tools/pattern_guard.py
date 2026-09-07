#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pattern_guard.py — Anti-Pattern Guardrail (T3)

Industry anchor: BP-03 Netflix Guardrails-not-Gates
Skill dependency: impl-coach (domain/pattern-selection.md anti-pattern list)

CLI:
  python3 tools/pattern_guard.py run
  python3 tools/pattern_guard.py run --file src/orders/service.py --strict --dry-run
"""
import os, sys, re, io, csv, argparse, datetime

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORT = os.path.join(ROOT, "台账", "41_模式护栏.csv")

MAX_LINES = 500
MAX_METHODS = 15
MAX_DEPTH = 4

EMPTY_EXCEPT_RE = re.compile(r"except\s+\w*\s*:\s*(pass|\.\.\.\s*$)", re.MULTILINE)
EMPTY_CATCH_RE = re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}", re.MULTILINE)
HARDCODED_URL_RE = re.compile(r"""=\s*['"]https?://[^'"]+['"]""")
HARDCODED_SECRET_RE = re.compile(r"""(?:password|secret|api_key|token|apikey)\s*=\s*['"][^'"]{4,}['"]""", re.IGNORECASE)
SVC_LOCATOR_RE = re.compile(r"(?:get_service|locate|resolve|injector\.get|container\.resolve)\s*\(", re.IGNORECASE)

def _lines(fp):
    try:
        with open(fp, "r", encoding="utf-8", errors="replace") as f: return sum(1 for _ in f)
    except: return 0

def _methods(fp):
    try:
        with open(fp, "r", encoding="utf-8", errors="replace") as f: c = f.read()
        return len(re.findall(r"^\s+def\s+\w+", c, re.MULTILINE))
    except: return 0

def _depth(fp):
    try:
        with open(fp, "r", encoding="utf-8", errors="replace") as f: lines = f.readlines()
    except: return 0
    mx = 0
    for l in lines:
        s = l.lstrip()
        if s and not s.startswith("#"):
            mx = max(mx, (len(l) - len(s)) // 4)
    return mx

def _check(fp, rel):
    findings = []
    ext = os.path.splitext(fp)[1]
    lc = _lines(fp)
    if lc > MAX_LINES:
        findings.append({"pattern":"God Object","file":rel,"detail":f"{lc} lines (max {MAX_LINES})","severity":"WARN","fix":"Split into smaller modules"})
    if ext == ".py":
        mc = _methods(fp)
        if mc > MAX_METHODS:
            findings.append({"pattern":"God Object","file":rel,"detail":f"{mc} methods (max {MAX_METHODS})","severity":"WARN","fix":"Split by responsibility"})
        dp = _depth(fp)
        if dp > MAX_DEPTH:
            findings.append({"pattern":"Deep Nesting","file":rel,"detail":f"depth {dp} (max {MAX_DEPTH})","severity":"HINT","fix":"Extract sub-functions / use guard clauses"})
    try:
        with open(fp, "r", encoding="utf-8", errors="replace") as f: content = f.read()
    except: return findings

    if ext == ".py" and EMPTY_EXCEPT_RE.search(content):
        findings.append({"pattern":"Swallowed Exception","file":rel,"detail":"empty except/pass","severity":"WARN","fix":"Log or use specific exception type"})
    if ext in (".ts",".tsx",".js") and EMPTY_CATCH_RE.search(content):
        findings.append({"pattern":"Swallowed Exception","file":rel,"detail":"empty catch block","severity":"WARN","fix":"At least console.error or rethrow"})
    if HARDCODED_URL_RE.search(content):
        findings.append({"pattern":"Hardcoded Config","file":rel,"detail":"hardcoded URL/IP","severity":"WARN","fix":"Externalize to config/env"})
    if HARDCODED_SECRET_RE.search(content):
        findings.append({"pattern":"Hardcoded Secret","file":rel,"detail":"hardcoded secret/password","severity":"BLOCK","fix":"Use secret manager, never store plaintext"})
    if ext == ".py" and SVC_LOCATOR_RE.search(content):
        findings.append({"pattern":"Service Locator","file":rel,"detail":"dynamic service lookup","severity":"HINT","fix":"Use constructor injection (DI)"})
    return findings

def _scan(target, file_filter=None):
    exts = {".py",".ts",".tsx",".js",".jsx"}
    if file_filter:
        full = os.path.join(ROOT, file_filter) if not os.path.isabs(file_filter) else file_filter
        return [full] if os.path.isfile(full) else []
    files = []
    for dp, dns, fns in os.walk(target):
        dns[:] = [d for d in dns if not d.startswith(".") and d not in ("node_modules","__pycache__",".venv","venv","tests","__tests__")]
        for fn in fns:
            if os.path.splitext(fn)[1] in exts: files.append(os.path.join(dp, fn))
    return files

def run(args):
    target = os.path.join(ROOT, "src") if not args.file else ROOT
    files = _scan(target, args.file)
    all_f = []
    for fp in files:
        all_f.extend(_check(fp, os.path.relpath(fp, ROOT)))

    blocks = [f for f in all_f if f["severity"] == "BLOCK"]
    warns = [f for f in all_f if f["severity"] == "WARN"]
    hints = [f for f in all_f if f["severity"] == "HINT"]

    if args.dry_run:
        print(f"[pattern-guard] dry-run: {len(files)} files, BLOCK={len(blocks)} WARN={len(warns)} HINT={len(hints)}")
        for f in all_f[:20]:
            print(f"  [{f['severity']}] {f['pattern']}: {f['file']} - {f['detail']}")
        return 0

    if all_f:
        header = ["Time","Anti-Pattern","File","Detail","Severity","Fix"]
        new = not os.path.exists(REPORT)
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with io.open(REPORT, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(header)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for fi in all_f:
                w.writerow([now, fi["pattern"], fi["file"], fi["detail"], fi["severity"], fi["fix"]])

    status = "FAIL" if (args.strict and blocks) else ("WARN" if warns else "PASS")
    print(f"[pattern-guard] {len(files)} files | BLOCK={len(blocks)} WARN={len(warns)} HINT={len(hints)} | mode={'strict' if args.strict else 'soft'} decision={status}")
    return 1 if (args.strict and blocks) else 0

def main():
    ap = argparse.ArgumentParser(description="Pattern Guard (T3)")
    sub = ap.add_subparsers(dest="command")
    r = sub.add_parser("run")
    r.add_argument("--file", default="")
    r.add_argument("--strict", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.command == "run": sys.exit(run(args))
    ap.print_help()

if __name__ == "__main__":
    main()
