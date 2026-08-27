#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opencode 会话库路径修复工具（项目迁移后遗症清理）

背景：项目目录迁移后，opencode 本地数据库中历史会话的消息 cwd / 事件流仍记录
旧路径；恢复会话或旧入口新建会话时对旧路径做 realPath 失败（ENOENT），表现为
「发消息无任何反应」。

用法：
  python tools/opencode_path_fix.py --scan
      扫描报告：找出库内登记但磁盘上已不存在的「死亡根目录」，并统计残留引用数。
  python tools/opencode_path_fix.py --fix --map "D:\\trae=>D:\\MyProjects"
      应用映射修复（可多次 --map）。自动覆盖 正斜杠/单反斜杠/JSON转义双反斜杠 三种形态。
  可选：--db <路径> 覆盖默认库位置；--backup-dir <目录> 指定备份目录（默认 .backup）。

安全机制：
  1) 独占锁预检——opencode 正在运行时拒绝执行；
  2) 写前自动备份数据库；
  3) 提交后执行 WAL checkpoint(TRUNCATE)，并复验残留为 0；
  4) 默认只读（不带 --fix 不写库）。

跨平台：Windows / macOS / Linux 通用；数据库按常见位置自动探测。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime


def q(s: str) -> str:
    """SQL 字符串字面量转义。"""
    return "'" + s.replace("'", "''") + "'"


def find_default_db() -> str | None:
    """按常见位置探测 opencode.db。"""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".local", "share", "opencode", "opencode.db"),
        os.path.join(os.environ.get("XDG_DATA_HOME", home + "/.local/share"), "opencode", "opencode.db"),
        os.path.join(home, "Library", "Application Support", "opencode", "opencode.db"),
        os.path.join(home, ".config", "opencode", "opencode.db"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def all_tables(cur: sqlite3.Cursor) -> list[str]:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall()]


def list_text_columns(cur: sqlite3.Cursor, table: str) -> list[str]:
    cur.execute(f'PRAGMA table_info("{table}")')
    return [r[1] for r in cur.fetchall()
            if r[2].upper() in ("TEXT", "VARCHAR", "CHAR", "CLOB") or r[2] == ""]


def registered_roots(cur: sqlite3.Cursor) -> set[str]:
    """从 project/project_directory/session 三张小表收集登记过的目录根。"""
    roots: set[str] = set()
    probes = [
        ("project", "worktree"),
        ("project_directory", "directory"),
        ("session", "directory"),
        ("session", "path"),
    ]
    for t, c in probes:
        try:
            cur.execute(f'SELECT DISTINCT "{c}" FROM "{t}"')
            for (v,) in cur.fetchall():
                if v and isinstance(v, str) and len(v) > 2 and v[1] == ":":
                    roots.add(v.rstrip("/\\"))
        except sqlite3.Error:
            continue
    return roots


def count_refs(cur: sqlite3.Cursor, root: str) -> dict[str, int]:
    """统计某根路径在各表各列的残留引用行数（裸根 LIKE 即覆盖三种形态）。"""
    like_variants = [root.replace("\\", "\\\\"), root.replace("\\", "/")]
    result: dict[str, int] = {}
    for t in all_tables(cur):
        for c in list_text_columns(cur, t):
            try:
                n = 0
                for lv in like_variants:
                    cur.execute(f'SELECT COUNT(*) FROM "{t}" WHERE "{c}" LIKE ?', (f"%{lv}%",))
                    n += cur.fetchone()[0]
                if n:
                    result[f"{t}.{c}"] = n
            except sqlite3.Error:
                continue
    return result


def build_pairs(old: str, new: str) -> list[tuple[str, str]]:
    """生成有序替换对：长形态在前（含尾分隔符优先于裸根）。"""
    o_b, n_b = old.rstrip("/\\"), new.rstrip("/\\")
    o_f, n_f = o_b.replace("\\", "\\\\"), n_b.replace("\\", "\\\\")
    o_s, n_s = o_b.replace("\\", "/"), n_b.replace("\\", "/")
    return [
        (o_f + "\\\\", n_f + "\\\\"),
        (o_b + "\\", n_b + "\\"),
        (o_s + "/", n_s + "/"),
        (o_f, n_f),
        (o_b, n_b),
        (o_s, n_s),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="opencode 会话库路径修复工具")
    ap.add_argument("--db", help="opencode.db 路径（默认自动探测）")
    ap.add_argument("--scan", action="store_true", help="只扫描报告，不写库")
    ap.add_argument("--fix", action="store_true", help="应用 --map 映射修复写库")
    ap.add_argument("--map", action="append", default=[], metavar="OLD=>NEW",
                    help="路径映射，可多次")
    ap.add_argument("--backup-dir", default=".backup", help="备份目录（默认 .backup）")
    args = ap.parse_args()

    db = args.db or find_default_db()
    if not db or not os.path.isfile(db):
        print("错误：未找到 opencode.db，请用 --db 指定路径。")
        return 1
    print(f"目标库：{db}")

    con = sqlite3.connect(db, timeout=10)
    cur = con.cursor()

    mappings: list[tuple[str, str]] = []
    for m in args.map:
        if "=>" not in m:
            print(f"错误：--map 格式应为 'OLD=>NEW'，收到：{m}")
            con.close()
            return 1
        old, new = m.split("=>", 1)
        mappings.append((old.strip().rstrip("/\\"), new.strip().rstrip("/\\")))

    # ---------- 扫描模式 ----------
    if not args.fix:
        roots = registered_roots(cur)
        dead = [r for r in sorted(roots) if not os.path.isdir(r)]
        if not dead:
            print("扫描完成：登记目录均在磁盘上存在，无死亡根路径。")
        for r in dead:
            print(f"\n[死亡根目录] {r}")
            refs = count_refs(cur, r)
            for k, v in sorted(refs.items()):
                print(f"    {k}: {v} 行")
            print(f"    合计引用：{sum(refs.values())} 行")
        con.close()
        print("\n（只读扫描模式；如需修复请加 --fix --map \"旧=>新\"）")
        return 0

    # ---------- 修复模式 ----------
    if not mappings:
        print("错误：--fix 需要至少一个 --map \"OLD=>NEW\"。可先 --scan 查看死亡根目录。")
        con.close()
        return 1

    try:
        cur.execute("BEGIN EXCLUSIVE")
        cur.execute("ROLLBACK")
    except sqlite3.OperationalError as e:
        print(f"错误：数据库被占用（{e}）。请先完全退出所有 opencode 实例再运行本工具。")
        con.close()
        return 2

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.abspath(args.backup_dir)
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"opencode_db_{ts}.db")
    shutil.copy2(db, backup_path)
    for ext in ("-wal", "-shm"):
        side = db + ext
        if os.path.isfile(side):
            shutil.copy2(side, backup_path + ext)
    print(f"已备份：{backup_path}")

    total = 0
    for old, new in mappings:
        pairs = build_pairs(old, new)
        like_probe = old.replace("\\", "\\\\")
        for t in all_tables(cur):
            for c in list_text_columns(cur, t):
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{t}" WHERE "{c}" LIKE ?', (f"%{like_probe}%",))
                    n = cur.fetchone()[0]
                    if not n:
                        continue
                    expr = f'"{c}"'
                    for o, nw in pairs:
                        expr = f"REPLACE({expr}, {q(o)}, {q(nw)})"
                    sql = f'UPDATE "{t}" SET "{c}"={expr} WHERE "{c}" LIKE ?'
                    cur.execute(sql, (f"%{like_probe}%",))
                    print(f"[{t}.{c}] 匹配 {n} 行，更新 {cur.rowcount} 行")
                    total += cur.rowcount
                except sqlite3.Error as e:
                    print(f"[{t}.{c}] 跳过：{e}")

    con.commit()
    try:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error as e:
        print(f"checkpoint 警告：{e}")

    left_total = 0
    for old, _new in mappings:
        refs = count_refs(cur, old)
        left_total += sum(refs.values())
    con.close()

    print(f"\n总更新行数：{total}")
    print(f"残留引用：{left_total}")
    if left_total == 0:
        print("DONE：全部旧路径已归位。现在可重新启动 opencode。")
        return 0
    print("WARN：仍有残留，请检查映射是否遗漏其他旧根目录（可用 --scan 再查）。")
    return 3


if __name__ == "__main__":
    sys.exit(main())
