#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成本估算器（estimate_cost）：大批量任务成本预警的落地工具。

读取 references/dev_platform_catalog.md 的价格快照，按模型 + 估算 token 计算费用，
可选追加一行到 台账/40_大模型成本台账.csv，支撑编排器「大批量任务成本预警」(§2.2-9)。

用法:
  python3 tools/estimate_cost.py --model "qwen2.5-coder:7b" --in-tok 200000 --out-tok 50000
  python3 tools/estimate_cost.py --model opus-4.8 --in-tok 50000 --out-tok 20000 --scenario "端到端特性" --platform opencode --tier S3 --batch --append

价格解析：在 catalog §2 表格中按模型名子串匹配，取「输入 $/MTok」「输出 $/MTok」两列；
「免费/免费额度」按 0 计。解析失败回退内置少量常见价格。
"""
import os
import re
import sys
import argparse
from datetime import datetime

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, ".trae", "skills", "references", "dev_platform_catalog.md")
LEDGER = os.path.join(ROOT, "台账", "40_大模型成本台账.csv")

# 解析失败时的内置兜底（输入/输出 $/MTok，近似快照 2026-08-27）
FALLBACK = {
    "qwen2.5-coder:7b": (0, 0), "qwen2.5:7b": (0, 0), "qwen3-8b": (0, 0),
    "glm-4.7-flash": (0, 0), "deepseek-v3": (0.44, 1.10), "deepseek-r1": (1.0, 2.0),
    "haiku-4.5": (1, 5), "sonnet-4.6": (3, 15), "gpt-terra": (2.5, 15),
    "gpt-sol": (5, 30), "opus-4.8": (5, 25), "gemini-3.1-pro": (2, 12), "gemini-3.5-flash": (1.5, 9),
}


def _to_price(cell):
    s = cell.strip().lower()
    if "免费" in s:
        return 0.0
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else 0.0


def load_prices(catalog_path):
    """返回 {模型名小写: (in_price, out_price)}，覆盖 §2.1/§2.2 两张表。"""
    prices = {}
    if not os.path.isfile(catalog_path):
        return prices
    with open(catalog_path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # §2 表结构含「模型」列，取模型名与紧随其后的 输入/输出 价格列
            if len(cells) < 4:
                continue
            # 在 cells[1] 找模型名（层/模型/输入/输出...），输入价格通常在模型后第1、2列
            model = cells[1]
            try:
                in_p = _to_price(cells[2])
                out_p = _to_price(cells[3])
            except Exception:
                continue
            prices[model.lower()] = (in_p, out_p)
    return prices


def find_price(model_arg, prices):
    key = model_arg.lower()
    # 精确或子串匹配
    if key in prices:
        return prices[key], key
    for name, pv in prices.items():
        if key in name or name in key:
            return pv, name
    # 回退内置
    if key in FALLBACK:
        return FALLBACK[key], key
    for name, pv in FALLBACK.items():
        if key in name or name in key:
            return pv, name
    return None, key


def main():
    ap = argparse.ArgumentParser(description="大模型成本估算器")
    ap.add_argument("--model", required=True, help="模型名（与 catalog §2 中名称子串匹配）")
    ap.add_argument("--in-tok", type=int, required=True, help="估算输入 token 数")
    ap.add_argument("--out-tok", type=int, required=True, help="估算输出 token 数")
    ap.add_argument("--scenario", default="", help="场景说明")
    ap.add_argument("--platform", default="", help="使用平台/工具")
    ap.add_argument("--tier", default="", help="档位 S0-S3")
    ap.add_argument("--batch", action="store_true", help="是否批量任务")
    ap.add_argument("--catalog", default=CATALOG, help="catalog 路径（默认 .trae/skills/references/dev_platform_catalog.md）")
    ap.add_argument("--ledger", default=LEDGER, help="成本台账路径")
    ap.add_argument("--append", action="store_true", help="追加一行到成本台账")
    args = ap.parse_args()

    prices = load_prices(args.catalog)
    pv, matched = find_price(args.model, prices)
    if pv is None:
        print(f"[WARN] 未在 catalog / 内置兜底中找到模型「{args.model}」，无法估算；请补充 catalog §2。")
        sys.exit(2)

    in_p, out_p = pv
    cost = args.in_tok / 1_000_000 * in_p + args.out_tok / 1_000_000 * out_p
    print("=" * 56)
    print(f"模型匹配 : {matched}  (输入 ${in_p}/MTok, 输出 ${out_p}/MTok)")
    print(f"估算输入 : {args.in_tok:,} tok  →  ${args.in_tok/1_000_000*in_p:.4f}")
    print(f"估算输出 : {args.out_tok:,} tok  →  ${args.out_tok/1_000_000*out_p:.4f}")
    print(f"估算总费用: ${cost:.4f}  (≈¥{cost*7.2:.4f})")
    if args.batch:
        print("任务类型 : 批量（建议本地/低价档：见 catalog §4）")
    print("=" * 56)

    if args.append:
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            args.scenario or "-", args.scenario, args.platform or "-", matched,
            args.tier or "-", "是" if args.batch else "否",
            str(args.in_tok), str(args.out_tok),
            f"{cost:.4f}", "", "", f"估算(estimate_cost.py); matched={matched}",
        ]
        header = "日期,任务,场景,平台,模型,档位(S0-S3),是否批量,估算输入tok,估算输出tok,估算费用$,实际费用$,结果,备注"
        line = ",".join(row) + "\n"
        with open(args.ledger, "a", encoding="utf-8") as fh:
            if fh.tell() == 0:
                fh.write(header + "\n")
            fh.write(line)
        print(f"[OK] 已追加到台账: {args.ledger}")
    else:
        print("[提示] 加 --append 可将本估算写入 台账/40_大模型成本台账.csv")


if __name__ == "__main__":
    main()
