#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""impl_advisor.py — Implementation Advisory Card Generator (T2)

Industry anchor: BP-02 DORA Shift-Left + BP-06 AI-Augmented Development
Skill dependency: impl-coach + role-development

CLI:
  python3 tools/impl_advisor.py advise --module orders
  python3 tools/impl_advisor.py advise --module orders --file src/orders/service.py
  python3 tools/impl_advisor.py advise --module orders --json
  python3 tools/impl_advisor.py list-context
"""
import os, sys, re, json, argparse, datetime

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.path.join(ROOT, ".trae", "skills")

# ─── ADR scanning ──────────────────────────────────────────
ADR_DIRS = [os.path.join(ROOT, d) for d in ["docs", os.path.join("docs","adr"),
              os.path.join(ROOT,"架构资产"), ROOT]]
ADR_NUM_RE = re.compile(r"ADR[- ]?(\d+)", re.IGNORECASE)
ADR_STATUS_RE = re.compile(r"(?:status|状态)\s*[:：]\s*(.+)", re.IGNORECASE)
ADR_DECISION_RE = re.compile(r"(?:decision|决策)\s*[:：]\s*(.+)", re.IGNORECASE)

def _scan_adrs():
    results, seen = [], set()
    for sd in ADR_DIRS:
        if not os.path.isdir(sd): continue
        for dp, _, fns in os.walk(sd):
            for fn in fns:
                if not fn.lower().endswith((".md",".csv",".txt")): continue
                if "adr" not in fn.lower() and "decision" not in fn.lower(): continue
                fp = os.path.join(dp, fn)
                if fp in seen: continue
                seen.add(fp)
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read(8192)
                except: continue
                nums = ADR_NUM_RE.findall(content)
                if not nums: continue
                sm = ADR_STATUS_RE.search(content)
                dm = ADR_DECISION_RE.search(content)
                title = fn
                for line in content.split("\n")[:5]:
                    if line.startswith("#"): title = line.lstrip("#").strip(); break
                for n in nums:
                    results.append({"path": os.path.relpath(fp, ROOT), "number": f"ADR-{n}",
                        "title": title,
                        "status": sm.group(1).strip() if sm else "unknown",
                        "decision": dm.group(1).strip()[:100] if dm else ""})
    return results

# ─── Context detection ─────────────────────────────────────
def _detect_layer(module, file_path=""):
    p = (file_path or module).lower()
    if any(k in p for k in ["presentation","controller","router","view","route"]): return "presentation"
    if any(k in p for k in ["data","repository","persistence","dao","model"]): return "data"
    return "business"

def _detect_lang():
    for f in os.listdir(ROOT):
        if f in ("pyproject.toml","requirements.txt"): return "python"
        if f in ("package.json","tsconfig.json"): return "typescript"
    return "python"

def _find_module_adrs(module, all_adrs):
    related = []
    kw = module.lower()
    for adr in all_adrs:
        hint = (adr["title"]+" "+adr["decision"]).lower()
        if kw in hint: related.append(adr)
    for adr in all_adrs:
        if adr in related: continue
        if any(k in adr["title"].lower() for k in ["架构","分层","框架","技术选型","认证","安全"]):
            if adr["status"] in ("已批准","accepted","approved"): related.append(adr)
    return related

def _load_coding_rules():
    rules = []
    cp = os.path.join(SKILLS_DIR, "role-development", "domain", "coding.md")
    if os.path.isfile(cp):
        with open(cp, "r", encoding="utf-8") as f: content = f.read()
        in_table = False
        for line in content.split("\n"):
            if "编码铁律" in line or "编码强制规则" in line: in_table = True; continue
            if in_table and line.startswith("|") and "---" not in line and "规则" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2: rules.append(f"{parts[0]}: {parts[1]}")
            if in_table and not line.strip() and rules: break
    return rules or ["Modular: files > 500 lines must be split", "Input: all external input must be validated",
        "Dependencies: no circular dependencies", "Config: no hardcoded configuration"]

def _suggest_patterns(module, layer, adrs):
    s = []
    txt = " ".join(a.get("decision","")+" "+a.get("title","") for a in adrs).lower()
    if any(k in txt for k in ["分层","依赖注入"]): s.append(("Dependency Injection", "architecture requires layered decoupling"))
    if any(k in txt for k in ["事件","异步","消息"]): s.append(("Observer/Pub-Sub", "event-driven architecture"))
    if any(k in txt for k in ["认证","jwt","安全"]): s.append(("Middleware/Decorator", "auth as cross-cutting concern"))
    if layer == "business": s.append(("Repository", "data access abstraction")); s.append(("Strategy", "replaceable business algorithms"))
    elif layer == "presentation": s.append(("DTO/Request-Response", "data transformation at boundary"))
    elif layer == "data": s.append(("Unit of Work", "transaction boundary management"))
    return s

def _gen_card(module, file_path, adrs, rules, patterns, layer, lang):
    L = [f"## Implementation Advisory: {module}", "",
         f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
         f"Layer: {layer}  Lang: {lang}"]
    if file_path: L.append(f"Target: {file_path}")
    L.append("")
    L.append("### Architecture Constraints")
    if adrs:
        for a in adrs:
            icon = "[OK]" if a["status"] in ("已批准","accepted","approved") else "[..]"
            L.append(f"- {icon} {a['number']}: {a['decision'] or a['title']}")
    else: L.append("- (No ADR documents found - consider completing architecture design first)")
    L += ["", "### Dependency Rules"]
    dep = {"presentation": "Can depend on Business, NOT on Data directly",
           "business": "Can depend on Data, NOT on Presentation",
           "data": "Cannot depend on Presentation or Business"}
    L.append(f"- {dep.get(layer, 'follow architecture layers')}")
    L += ["", "### Recommended Patterns"]
    if patterns:
        for n, r in patterns: L.append(f"- **{n}** (reason: {r})")
    else: L.append("- (no specific patterns recommended)")
    L += ["", "### Coding Rules (from role-development)"]
    for r in rules: L.append(f"- {r}")
    L += ["", "### Scaffold Command",
          f"- `python3 tools/scaffold_cli.py create --name {module} --layer {layer} --lang {lang}`",
          "", "### Implementation Steps",
          "1. Run scaffold_cli to generate module skeleton",
          "2. Define interfaces (interface.py) - match architecture contracts",
          "3. Implement DTOs / data models",
          "4. Implement business logic (service.py) - follow recommended patterns",
          "5. Write unit tests (fail first, then implement, then refactor)",
          "6. Run pattern_guard to check for anti-patterns",
          "", "### Related Skills",
          "- impl-coach: architecture-to-code translation, pattern selection",
          "- role-development: coding standards, secure coding",
          "- role-architecture: architecture views, ADR documents", ""]
    return "\n".join(L)

def cmd_advise(args):
    module, fp = args.module, args.file or ""
    all_adrs = _scan_adrs()
    layer = _detect_layer(module, fp)
    lang = _detect_lang()
    mod_adrs = _find_module_adrs(module, all_adrs)
    rules = _load_coding_rules()
    patterns = _suggest_patterns(module, layer, mod_adrs)
    card = _gen_card(module, fp, mod_adrs, rules, patterns, layer, lang)
    if args.json:
        print(json.dumps({"module": module, "layer": layer, "lang": lang,
            "adrs": [{"number": a["number"], "title": a["title"], "status": a["status"]} for a in mod_adrs],
            "patterns": [{"name": n, "reason": r} for n, r in patterns],
            "coding_rules": rules, "advisory_card": card}, ensure_ascii=False, indent=2))
    else: print(card)
    return 0

def cmd_list_context(args):
    adrs = _scan_adrs()
    print(f"[impl-advisor] Project context overview")
    print(f"  ADR documents: {len(adrs)}")
    for a in adrs[:10]: print(f"    - {a['number']}: {a['title']} [{a['status']}]")
    skills = sorted([n for n in os.listdir(SKILLS_DIR) if os.path.isdir(os.path.join(SKILLS_DIR, n))]) if os.path.isdir(SKILLS_DIR) else []
    print(f"  Available skills: {len(skills)}")
    for s in skills: print(f"    - {s}")
    rules = _load_coding_rules()
    print(f"  Coding rules: {len(rules)}")
    print(f"  Project lang: {_detect_lang()}")
    return 0

def main():
    ap = argparse.ArgumentParser(description="Implementation Advisor (T2)")
    sub = ap.add_subparsers(dest="command")
    adv = sub.add_parser("advise", help="Generate advisory card")
    adv.add_argument("--module", required=True)
    adv.add_argument("--file", default="")
    adv.add_argument("--json", action="store_true")
    sub.add_parser("list-context", help="List project context")
    args = ap.parse_args()
    if args.command == "advise": sys.exit(cmd_advise(args))
    elif args.command == "list-context": sys.exit(cmd_list_context(args))
    else: ap.print_help()

if __name__ == "__main__":
    main()
