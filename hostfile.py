#!/usr/bin/env python3
"""hostfile - Manage /etc/hosts entries.

One file. Zero deps. Control your DNS.

Usage:
  hostfile.py list                         → show all entries
  hostfile.py add 127.0.0.1 myapp.local   → add entry
  hostfile.py rm myapp.local               → remove entry
  hostfile.py search "local"               → search entries
  hostfile.py backup                       → backup hosts file
  hostfile.py disable myapp.local          → comment out entry
  hostfile.py enable myapp.local           → uncomment entry
  hostfile.py export                       → export as JSON
"""

import argparse
import json
import os
import re
import shutil
import sys
import time

HOSTS = "/etc/hosts"


def read_hosts() -> list[str]:
    with open(HOSTS) as f:
        return f.readlines()


def write_hosts(lines: list[str]):
    with open(HOSTS, "w") as f:
        f.writelines(lines)


def parse_line(line: str) -> dict | None:
    stripped = line.strip()
    disabled = stripped.startswith("#")
    clean = stripped.lstrip("# ")
    m = re.match(r'^(\S+)\s+(.+)$', clean)
    if m and not clean.startswith("#"):
        ip = m.group(1)
        if re.match(r'^[\d.:a-fA-F]+$', ip):
            hosts = m.group(2).split()
            return {"ip": ip, "hosts": hosts, "disabled": disabled, "raw": line}
    return None


def cmd_list(args):
    lines = read_hosts()
    for i, line in enumerate(lines, 1):
        entry = parse_line(line)
        if entry:
            status = "# " if entry["disabled"] else "  "
            print(f"{status}{entry['ip']:20s} {' '.join(entry['hosts'])}")


def cmd_add(args):
    lines = read_hosts()
    new_line = f"{args.ip}\t{args.hostname}\n"
    # Check if already exists
    for line in lines:
        entry = parse_line(line)
        if entry and args.hostname in entry["hosts"] and not entry["disabled"]:
            print(f"  ⚠️  '{args.hostname}' already points to {entry['ip']}")
            return 1
    lines.append(new_line)
    write_hosts(lines)
    print(f"  ✅ Added: {args.ip} → {args.hostname}")


def cmd_rm(args):
    lines = read_hosts()
    new_lines = []
    removed = False
    for line in lines:
        entry = parse_line(line)
        if entry and args.hostname in entry["hosts"]:
            remaining = [h for h in entry["hosts"] if h != args.hostname]
            if remaining:
                new_lines.append(f"{entry['ip']}\t{' '.join(remaining)}\n")
            removed = True
        else:
            new_lines.append(line)
    if removed:
        write_hosts(new_lines)
        print(f"  ✅ Removed: {args.hostname}")
    else:
        print(f"  '{args.hostname}' not found")
        return 1


def cmd_search(args):
    lines = read_hosts()
    found = 0
    for line in lines:
        entry = parse_line(line)
        if entry:
            text = f"{entry['ip']} {' '.join(entry['hosts'])}"
            if args.pattern.lower() in text.lower():
                status = "# " if entry["disabled"] else "  "
                print(f"{status}{entry['ip']:20s} {' '.join(entry['hosts'])}")
                found += 1
    if not found:
        print(f"  No entries matching '{args.pattern}'")


def cmd_backup(args):
    ts = time.strftime("%Y%m%d_%H%M%S")
    dest = f"/tmp/hosts_backup_{ts}"
    shutil.copy2(HOSTS, dest)
    print(f"  ✅ Backed up to {dest}")


def cmd_toggle(args, disable: bool):
    lines = read_hosts()
    new_lines = []
    toggled = False
    for line in lines:
        entry = parse_line(line)
        if entry and args.hostname in entry["hosts"]:
            if disable and not entry["disabled"]:
                new_lines.append("# " + line.lstrip("# "))
                toggled = True
            elif not disable and entry["disabled"]:
                new_lines.append(line.lstrip("# "))
                toggled = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    if toggled:
        write_hosts(new_lines)
        action = "Disabled" if disable else "Enabled"
        print(f"  ✅ {action}: {args.hostname}")
    else:
        print(f"  '{args.hostname}' not found or already {'disabled' if disable else 'enabled'}")


def cmd_export(args):
    lines = read_hosts()
    entries = []
    for line in lines:
        entry = parse_line(line)
        if entry:
            entries.append({"ip": entry["ip"], "hosts": entry["hosts"], "disabled": entry["disabled"]})
    print(json.dumps(entries, indent=2))


def main():
    p = argparse.ArgumentParser(description="Manage /etc/hosts")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("list")
    sub.add_parser("backup")
    sub.add_parser("export")

    s = sub.add_parser("add"); s.add_argument("ip"); s.add_argument("hostname")
    s = sub.add_parser("rm"); s.add_argument("hostname")
    s = sub.add_parser("search"); s.add_argument("pattern")
    s = sub.add_parser("disable"); s.add_argument("hostname")
    s = sub.add_parser("enable"); s.add_argument("hostname")

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return 1
    cmds = {"list": cmd_list, "add": cmd_add, "rm": cmd_rm, "search": cmd_search,
            "backup": cmd_backup, "disable": lambda a: cmd_toggle(a, True),
            "enable": lambda a: cmd_toggle(a, False), "export": cmd_export}
    return cmds[args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())
