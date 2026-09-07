#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adr_trace.py — ADR Traceability Scanner (T5)

Industry anchor: BP-05 Continuous Architecture (Erich Gamma)
Skill dependency: impl-coach (domain/adr-to-code.md traceability matrix)

CLI:
  python3 tools/adr_trace.py run
  python3 tools/adr_trace.py run --target src/ --dry-run
"""
import os, sys, re, io, csv, argparse, datetime

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORT = os.path.join(ROOT, "台账", "42_ADR追溯矩阵.csv")

CODE_ADR_RE = re.compile(r"(?:#|//|/\*)\s*ADR[- ]?(\d+)", re.IGNORECASE)
ADR_DOC_RE = re.compile(r"ADR[- ]?(\d+)", re.IGNORECASE)
ADR_STATUS_RE = re.compile(r"(?:status|状态)\s*[:：]\s*(\S+)", re.IGNORECASE)
SRC_EXTS = {".py",".ts",".tsx",".js",".jsx",".go",".java",".rb",".rs"}
ADR_DIRS = ["docs", os.path.join("docs","adr"), "架构资产", os.path.join("架构资产","adr"), "开发资产", ""]

def _scan_adr_docs():
    adrs, seen = {}, set()
    for rd in ADR_DIRS:
        sd = os.path.join(ROOT, rd) if rd else ROOT
        if not os.path.isdir(sd): continue
        for dp, _, fns in os.walk(sd):
            for fn in fns:
                if not fn.lower().endswith((".md",".csv",".txt")): continue
                if "adr" not in fn.lower() and "decision" not in fn.lower(): continue
                fp = os.path.join(dp, fn)
                if fp in seen: continue
                seen.add(fp)
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f: content = f.read(16384)
                except: continue
                nums = ADR_DOC_RE.findall(content)
                sm = ADR_STATUS_RE.search(content)
                status = sm.group(1).strip() if sm else "unknown"
                title = fn
                for line in content.split("\n")[:5]:
                    if line.startswith("#"): title = line.lstrip("#").strip(); break
                for n in nums:
                    key = f"ADR-{n}"
                    if key not in adrs:
                        adrs[key] = {"number":key,"path":os.path.relpath(fp,ROOT),"title":title,"status":status,"referenced":False}
    return adrs

def _scan_code_refs(target):
    refs = {}
    for dp, dns, fns in os.walk(target):
        dns[:] = [d for d in dns if not d.startswith(".") and d not in ("node_modules","__pycache__",".venv","venv")]
        for fn in fns:
            if os.path.splitext(fn)[1] not in SRC_EXTS: continue
            fp = os.path.join(dp, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    for ln, line in enumerate(f, 1):
                        for m in CODE_ADR_RE.finditer(line):
                            key = f"ADR-{m.group(1)}"
                            refs.setdefault(key, []).append({"file":os.path.relpath(fp,ROOT),"line":ln,"ctx":line.strip()[:80]})
            except: continue
    return refs

def run(args):
    target = os.path.join(ROOT, args.target) if args.target else ROOT
    if not os.path.isdir(target): target = ROOT
    adr_docs = _scan_adr_docs()
    code_refs = _scan_code_refs(target)
    findings = []

    for adr_num, ref_list in sorted(code_refs.items()):
        doc = adr_docs.get(adr_num)
        if doc:
            doc["referenced"] = True
            ok = doc["status"] in ("已批准","accepted","approved")
            for ref in ref_list:
                findings.append({"adr":adr_num,"type":"referenced","code":f"{ref['file']}:{ref['line']}",
                    "doc":doc["path"],"status":doc["status"],"verdict":"[OK] traceable" if ok else "[WARN] traceable but status="+doc["status"]})
        else:
            for ref in ref_list:
                findings.append({"adr":adr_num,"type":"ref_not_found","code":f"{ref['file']}:{ref['line']}",
                    "doc":"","status":"missing","verdict":"[FAIL] references non-existent ADR"})

    for adr_num, doc in sorted(adr_docs.items()):
        if not doc["referenced"] and doc["status"] in ("已批准","accepted","approved"):
            findings.append({"adr":adr_num,"type":"approved_not_referenced","code":"","doc":doc["path"],
                "status":doc["status"],"verdict":"[WARN] approved but no code reference - may not be implemented"})

    if args.dry_run:
        print(f"[adr-trace] dry-run: {len(adr_docs)} ADR docs, {len(code_refs)} code refs, {len(findings)} findings")
        for f in findings[:20]:
            print(f"  {f['adr']} [{f['type']}] {f['verdict']}")
        return 0

    if findings:
        header = ["Time","ADR","Type","Code Location","Doc Location","Status","Verdict"]
        new = not os.path.exists(REPORT)
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with io.open(REPORT, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(header)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for fi in findings:
                w.writerow([now,fi["adr"],fi["type"],fi["code"],fi["doc"],fi["status"],fi["verdict"]])

    traced = len([f for f in findings if f["type"]=="referenced"])
    missing = len([f for f in findings if f["type"]=="ref_not_found"])
    unref = len([f for f in findings if f["type"]=="approved_not_referenced"])
    print(f"[adr-trace] {len(adr_docs)} ADR docs | {traced} traced | {missing} not found | {unref} approved but not referenced")
    return 1 if missing > 0 else 0

def main():
    ap = argparse.ArgumentParser(description="ADR Traceability Scanner (T5)")
    sub = ap.add_subparsers(dest="command")
    r = sub.add_parser("run")
    r.add_argument("--target", default="")
    r.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.command == "run": sys.exit(run(args))
    ap.print_help()

if __name__ == "__main__":
    main()
