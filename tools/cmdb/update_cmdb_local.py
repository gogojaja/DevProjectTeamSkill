#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
读取本机配置并更新 CMDB —— 一次性注册脚本
用法: py -3.11 tools/cmdb/update_cmdb_local.py
"""

import os
import sys
import sqlite3
import platform
import subprocess
import socket
import ipaddress
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

CMDB_DB = Path(__file__).parent / "cmdb.db"
PROJECT = "DevProjectTeamSkill"
OPERATOR = os.getenv("USERNAME", os.getenv("USER", "unknown"))

# ── 本机信息 ──────────────────────────────────────
HOSTNAME = socket.gethostname()
ENVIRONMENT = "dev"


def get_local_ips():
    """获取本机 IPv4 地址（排除回环）"""
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ipaddress.ip_address(ip).is_loopback and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips


def get_software_list():
    """检测已安装的开发软件"""
    checks = {
        "git":      ["git", "--version"],
        "node":     ["node", "--version"],
        "npm":      ["npm", "--version"],
        "python":   ["python", "--version"],
        "python3":  ["python3", "--version"],
        "py":       ["py", "--version"],
        "java":     ["java", "-version"],
        "ffmpeg":   ["ffmpeg", "-version"],
        "code":     ["code", "--version"],
        "rg":       ["rg", "--version"],
        "wsl":      ["wsl", "--version"],
        "git-lfs":  ["git-lfs", "--version"],
        "7z":       ["7z", ""],
        "winget":   ["winget", "--version"],
        "powershell": ["powershell", "-Command", "$PSVersionTable.PSVersion.ToString()"],
    }
    results = []
    for name, cmd in checks.items():
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0 or r.stdout.strip() or r.stderr.strip():
                ver = (r.stdout.strip() or r.stderr.strip()).splitlines()[0]
                results.append((name, ver))
        except Exception:
            pass
    return results


def get_gpu_info():
    """获取 GPU 信息（Windows）"""
    gpus = []
    try:
        import ctypes
        import subprocess
        r = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stdout.strip().splitlines():
            line = line.strip()
            if line:
                gpus.append(line)
    except Exception:
        pass
    return gpus


def get_listening_ports():
    """获取非系统监听端口（Windows）"""
    ports = []
    try:
        r = subprocess.run(
            ["powershell", "-Command",
             "Get-NetTCPConnection -State Listen | "
             "Where-Object { $_.LocalPort -lt 10000 -and $_.LocalPort -notin @(135,139,445,5040,5357) } | "
             "Select-Object LocalPort, OwningProcess -Unique | Sort-Object LocalPort"],
            capture_output=True, text=True, timeout=15
        )
        lines = r.stdout.strip().splitlines()[2:]  # 跳过表头
        port_pid = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    port = int(parts[0])
                    pid = int(parts[1])
                    port_pid.append((port, pid))
                except ValueError:
                    continue

        # 查进程名
        for port, pid in port_pid:
            proc_name = "unknown"
            try:
                pr = subprocess.run(
                    ["powershell", "-Command", f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName"],
                    capture_output=True, text=True, timeout=10
                )
                proc_name = pr.stdout.strip() or "unknown"
            except Exception:
                pass
            ports.append((port, proc_name))
    except Exception:
        pass
    return ports


def register_host(conn, hostname, ips, environment, operator):
    """注册或更新主机"""
    ip_str = ", ".join(ips) if ips else ""
    cursor = conn.execute("SELECT id FROM hosts WHERE hostname = ?", (hostname,))
    row = cursor.fetchone()
    if row:
        host_id = row[0]
        conn.execute("UPDATE hosts SET ip = ?, environment = ? WHERE id = ?",
                     (ip_str, environment, host_id))
        print(f"  主机已更新: {hostname} (id={host_id}, ip={ip_str})")
    else:
        conn.execute(
            "INSERT INTO hosts (hostname, ip, environment, registered_by) VALUES (?, ?, ?, ?)",
            (hostname, ip_str, environment, operator)
        )
        host_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        print(f"  主机已注册: {hostname} (id={host_id}, ip={ip_str})")
    conn.commit()
    return host_id


def register_resource(conn, host_id, rtype, identifier, name, project, priority="medium", notes=""):
    """注册或更新资源"""
    cursor = conn.execute(
        "SELECT id, occupied_by, status FROM resources WHERE host_id = ? AND resource_type = ? AND resource_identifier = ?",
        (host_id, rtype, identifier)
    )
    existing = cursor.fetchone()
    if existing:
        conn.execute(
            """UPDATE resources SET resource_name = ?, occupied_by = ?, status = 'occupied',
               priority = ?, notes = ?, released_at = NULL WHERE id = ?""",
            (name, project, priority, notes, existing[0])
        )
        print(f"  资源已更新: {rtype}={identifier} ({name})")
    else:
        conn.execute(
            """INSERT INTO resources (host_id, resource_type, resource_identifier, resource_name, occupied_by, status, priority, notes)
               VALUES (?, ?, ?, ?, ?, 'occupied', ?, ?)""",
            (host_id, rtype, identifier, name, project, priority, notes)
        )
        print(f"  资源已注册: {rtype}={identifier} ({name})")
    conn.commit()


def main():
    if not CMDB_DB.exists():
        print(f"❌ 数据库不存在，请先运行: py -3.11 tools/cmdb/cmdb-cli.py init")
        return 1

    conn = sqlite3.connect(CMDB_DB)

    # 1. 注册主机
    print(f"\n{'='*60}")
    print(f"主机: {HOSTNAME}")
    ips = get_local_ips()
    print(f"IP: {', '.join(ips)}")
    host_id = register_host(conn, HOSTNAME, ips, ENVIRONMENT, OPERATOR)

    # 2. 注册软件
    print(f"\n{'='*60}")
    print("注册软件资源...")
    sw_list = get_software_list()
    for name, version in sw_list:
        register_resource(conn, host_id, "software", name, version, PROJECT,
                          priority="high" if name in ("git", "node", "python", "py") else "medium")

    # 3. 注册 GPU
    print(f"\n{'='*60}")
    print("注册 GPU 资源...")
    gpus = get_gpu_info()
    for gpu in gpus:
        gpu_id = gpu.replace(" ", "-").replace("(", "").replace(")", "")
        register_resource(conn, host_id, "gpu", gpu_id, gpu, PROJECT, priority="medium")

    # 4. 注册端口
    print(f"\n{'='*60}")
    print("注册端口资源...")
    ports = get_listening_ports()
    for port, proc_name in ports:
        register_resource(conn, host_id, "port", str(port), proc_name, PROJECT,
                          priority="medium", notes=f"PID process: {proc_name}")

    # 5. 汇总
    print(f"\n{'='*60}")
    cursor = conn.execute("SELECT COUNT(*) FROM resources WHERE host_id = ?", (host_id,))
    total = cursor.fetchone()[0]
    print(f"✅ 注册完成: 主机 {HOSTNAME} 共 {total} 条资源记录")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
