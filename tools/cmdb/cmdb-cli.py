#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CMDB CLI - 轻量级资源管理工具
功能：主机注册、资源注册、资源释放、冲突检测、查询、导出
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# 配置
CMDB_DB = Path(__file__).parent / "cmdb.db"
CMDB_DIR = Path(__file__).parent.parent.parent.parent  # D:\trae\DevProjectTeamSkill
AUDIT_LOG = CMDB_DIR / "cmdb_audit.log"

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(CMDB_DB)
    conn.row_factory = sqlite3.Row
    return conn

def log_audit(action: str, resource_id: Optional[int], operator: str, notes: str = ""):
    """记录审计日志"""
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | {action} | resource_id={resource_id} | operator={operator} | notes={notes}\n")
    except Exception as e:
        print(f"⚠️  审计日志写入失败: {e}", file=sys.stderr)

def cmd_init(args):
    """初始化数据库"""
    if CMDB_DB.exists():
        print(f"⚠️  数据库已存在: {CMDB_DB}")
        return 1

    conn = get_db_connection()
    try:
        conn.executescript("""
        CREATE TABLE hosts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT UNIQUE NOT NULL,
            ip TEXT,
            environment TEXT DEFAULT 'dev',
            registered_by TEXT,
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );

        CREATE TABLE resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_id INTEGER NOT NULL,
            resource_type TEXT NOT NULL,
            resource_identifier TEXT NOT NULL,
            resource_name TEXT,
            occupied_by TEXT,
            status TEXT DEFAULT 'free',
            priority TEXT DEFAULT 'medium',
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
            released_at TEXT,
            notes TEXT
        );

        CREATE TABLE audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            resource_id INTEGER,
            operator TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );

        CREATE INDEX idx_resources_host_id ON resources(host_id);
        CREATE INDEX idx_resources_type ON resources(resource_type);
        CREATE INDEX idx_resources_occupied_by ON resources(occupied_by);
        CREATE INDEX idx_resources_status ON resources(status);
        """)
        conn.commit()
        print(f"✅ 数据库初始化完成: {CMDB_DB}")
        return 0
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()

def cmd_register(args):
    """注册资源"""
    if not CMDB_DB.exists():
        print(f"❌ 数据库不存在，请先运行: cmdb-cli init", file=sys.stderr)
        return 1

    conn = get_db_connection()
    try:
        # 检查主机是否存在
        cursor = conn.execute("SELECT id FROM hosts WHERE hostname = ?", (args.host,))
        host_row = cursor.fetchone()
        if not host_row:
            print(f"❌ 主机不存在: {args.host}", file=sys.stderr)
            return 1

        host_id = host_row["id"]

        # 检查资源是否已存在
        cursor = conn.execute(
            "SELECT id, occupied_by, status, resource_name FROM resources WHERE host_id = ? AND resource_type = ? AND resource_identifier = ?",
            (host_id, args.type, args.identifier)
        )
        existing = cursor.fetchone()

        if existing:
            print(f"⚠️  资源已存在: {args.type}={args.identifier} (id={existing['id']})")
            if existing["occupied_by"] and existing["occupied_by"] != args.project:
                print(f"   占用项目: {existing['occupied_by']}")
            print(f"   当前状态: {existing['status']}")
            if not args.force:
                print(f"   使用 --force 强制覆盖")
                return 1
            # --force：更新已有记录，不新建（避免残留旧记录）
            conn.execute(
                """UPDATE resources
                   SET resource_name = ?, occupied_by = ?, status = 'occupied', priority = ?, notes = ?,
                       released_at = NULL
                   WHERE id = ?""",
                (args.name or existing["resource_name"] or "", args.project, args.priority or "medium", args.notes or "", existing["id"])
            )
            resource_id = existing["id"]
            log_audit("register(force)", resource_id, args.operator, f"project={args.project}, priority={args.priority}")
            conn.commit()
            print(f"✅ 资源覆盖成功: {args.type}={args.identifier} (host={args.host}, project={args.project}, id={resource_id})")
            return 0

        # 资源不存在：插入新记录
        conn.execute(
            """INSERT INTO resources (host_id, resource_type, resource_identifier, resource_name, occupied_by, status, priority, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (host_id, args.type, args.identifier, args.name or "", args.project, "occupied", args.priority or "medium", args.notes or "")
        )

        # 记录审计
        resource_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        log_audit("register", resource_id, args.operator, f"project={args.project}, priority={args.priority}")

        conn.commit()
        print(f"✅ 资源注册成功: {args.type}={args.identifier} (host={args.host}, project={args.project})")
        return 0
    except sqlite3.IntegrityError as e:
        print(f"❌ 资源标识冲突: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 资源注册失败: {e}", file=sys.stderr)
        conn.rollback()
        return 1
    finally:
        conn.close()

def cmd_release(args):
    """释放资源"""
    if not CMDB_DB.exists():
        print(f"❌ 数据库不存在", file=sys.stderr)
        return 1

    conn = get_db_connection()
    try:
        # 检查资源是否存在
        if args.resource_id:
            cursor = conn.execute("SELECT id, occupied_by, status FROM resources WHERE id = ?", (args.resource_id,))
            resource = cursor.fetchone()
            if not resource:
                print(f"❌ 资源不存在: {args.resource_id}", file=sys.stderr)
                return 1
        elif args.type and args.identifier:
            cursor = conn.execute(
                "SELECT id, occupied_by, status FROM resources WHERE resource_type = ? AND resource_identifier = ?",
                (args.type, args.identifier)
            )
            resource = cursor.fetchone()
            if not resource:
                print(f"❌ 资源不存在: {args.type}={args.identifier}", file=sys.stderr)
                return 1
        else:
            print(f"❌ 请指定 --resource-id 或 --type --identifier", file=sys.stderr)
            return 1

        resource_id = resource["id"]
        if resource["occupied_by"] and resource["occupied_by"] != args.project:
            print(f"⚠️  资源当前占用项目: {resource['occupied_by']}", file=sys.stderr)
            if not args.force:
                return 1

        # 释放资源
        conn.execute(
            """UPDATE resources SET occupied_by = NULL, status = 'free', released_at = ?, notes = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), f"released by {args.project}", resource_id)
        )

        # 记录审计
        log_audit("release", resource_id, args.operator, f"project={args.project}")

        conn.commit()
        print(f"✅ 资源释放成功: {resource['id']}")
        return 0
    except Exception as e:
        print(f"❌ 资源释放失败: {e}", file=sys.stderr)
        conn.rollback()
        return 1
    finally:
        conn.close()

def cmd_query(args):
    """查询资源"""
    if not CMDB_DB.exists():
        print(f"❌ 数据库不存在", file=sys.stderr)
        return 1

    conn = get_db_connection()
    try:
        query = "SELECT r.id, h.hostname, r.resource_type, r.resource_identifier, r.occupied_by, r.status, r.priority, r.registered_at FROM resources r JOIN hosts h ON r.host_id = h.id WHERE 1=1"
        params = []

        if args.host:
            query += " AND h.hostname = ?"
            params.append(args.host)
        if args.type:
            query += " AND r.resource_type = ?"
            params.append(args.type)
        if args.project:
            query += " AND r.occupied_by = ?"
            params.append(args.project)
        if args.status:
            query += " AND r.status = ?"
            params.append(args.status)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            print("未找到匹配的资源")
            return 0

        # 表头
        print(f"{'ID':<5} {'主机':<20} {'类型':<10} {'标识':<15} {'占用项目':<20} {'状态':<10} {'优先级':<10} {'注册时间'}")
        print("-" * 100)

        for row in rows:
            print(f"{row['id']:<5} {row['hostname']:<20} {row['resource_type']:<10} {row['resource_identifier']:<15} {row['occupied_by'] or '-':<20} {row['status']:<10} {row['priority']:<10} {row['registered_at']}")

        return 0
    except Exception as e:
        print(f"❌ 查询失败: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()

def cmd_list_hosts(args):
    """列出所有主机"""
    if not CMDB_DB.exists():
        print(f"❌ 数据库不存在", file=sys.stderr)
        return 1

    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT id, hostname, ip, environment, registered_by, registered_at FROM hosts ORDER BY hostname")
        rows = cursor.fetchall()

        if not rows:
            print("未找到主机")
            return 0

        print(f"{'ID':<5} {'主机名':<20} {'IP':<15} {'环境':<10} {'注册人':<15} {'注册时间'}")
        print("-" * 70)

        for row in rows:
            print(f"{row['id']:<5} {row['hostname']:<20} {row['ip'] or '-':<15} {row['environment']:<10} {row['registered_by'] or '-':<15} {row['registered_at']}")

        return 0
    except Exception as e:
        print(f"❌ 查询失败: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()

def cmd_export(args):
    """导出资源为 CSV"""
    if not CMDB_DB.exists():
        print(f"❌ 数据库不存在", file=sys.stderr)
        return 1

    conn = get_db_connection()
    try:
        query = "SELECT r.id, h.hostname, r.resource_type, r.resource_identifier, r.occupied_by, r.status, r.priority, r.registered_at FROM resources r JOIN hosts h ON r.host_id = h.id WHERE 1=1"
        params = []

        if args.host:
            query += " AND h.hostname = ?"
            params.append(args.host)
        if args.type:
            query += " AND r.resource_type = ?"
            params.append(args.type)
        if args.project:
            query += " AND r.occupied_by = ?"
            params.append(args.project)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            print("未找到匹配的资源")
            return 0

        # 写入 CSV
        output = sys.stdout if args.output == "-" else args.output
        with open(output, "w", encoding="utf-8-sig") as f:
            f.write("ID,Hostname,ResourceType,ResourceIdentifier,OccupiedBy,Status,Priority,RegisteredAt\n")
            for row in rows:
                f.write(f"{row['id']},{row['hostname']},{row['resource_type']},{row['resource_identifier']},{row['occupied_by'] or ''},{row['status']},{row['priority']},{row['registered_at']}\n")

        print(f"✅ 导出成功: {output}")
        return 0
    except Exception as e:
        print(f"❌ 导出失败: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()

def cmd_version(args):
    """显示版本信息"""
    print(f"CMDB CLI v1.0.0")
    print(f"数据库: {CMDB_DB}")
    return 0

def main():
    parser = argparse.ArgumentParser(description="CMDB CLI - 轻量级资源管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init
    subparsers.add_parser("init", help="初始化数据库")

    # register
    register_parser = subparsers.add_parser("register", help="注册资源")
    register_parser.add_argument("--host", required=True, help="主机名")
    register_parser.add_argument("--type", required=True, choices=["port", "container", "model", "gpu", "database", "domain", "software"], help="资源类型")
    register_parser.add_argument("--identifier", required=True, help="资源标识（端口号/容器名/模型名）")
    register_parser.add_argument("--name", help="资源名称（可选）")
    register_parser.add_argument("--project", required=True, help="占用项目")
    register_parser.add_argument("--priority", choices=["high", "medium", "low"], help="优先级（默认：medium）")
    register_parser.add_argument("--notes", help="备注")
    register_parser.add_argument("--force", action="store_true", help="强制覆盖已存在的资源")
    register_parser.add_argument("--operator", default=os.getenv("USER", "unknown"), help="操作人（默认：环境变量 USER）")

    # release
    release_parser = subparsers.add_parser("release", help="释放资源")
    release_parser.add_argument("--resource-id", type=int, help="资源 ID（优先级高于 type+identifier）")
    release_parser.add_argument("--type", help="资源类型")
    release_parser.add_argument("--identifier", help="资源标识")
    release_parser.add_argument("--project", required=True, help="释放项目")
    release_parser.add_argument("--force", action="store_true", help="强制释放")
    release_parser.add_argument("--operator", default=os.getenv("USER", "unknown"), help="操作人")

    # query
    query_parser = subparsers.add_parser("query", help="查询资源")
    query_parser.add_argument("--host", help="主机名")
    query_parser.add_argument("--type", help="资源类型")
    query_parser.add_argument("--project", help="占用项目")
    query_parser.add_argument("--status", choices=["free", "occupied", "conflict"], help="状态筛选")

    # list-hosts
    subparsers.add_parser("list-hosts", help="列出所有主机")

    # export
    export_parser = subparsers.add_parser("export", help="导出资源为 CSV")
    export_parser.add_argument("--host", help="主机名")
    export_parser.add_argument("--type", help="资源类型")
    export_parser.add_argument("--project", help="占用项目")
    export_parser.add_argument("--output", default="-", help="输出文件（默认：stdout）")

    # version
    subparsers.add_parser("version", help="显示版本信息")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 执行命令
    if args.command == "init":
        return cmd_init(args)
    elif args.command == "register":
        return cmd_register(args)
    elif args.command == "release":
        return cmd_release(args)
    elif args.command == "query":
        return cmd_query(args)
    elif args.command == "list-hosts":
        return cmd_list_hosts(args)
    elif args.command == "export":
        return cmd_export(args)
    elif args.command == "version":
        return cmd_version(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
