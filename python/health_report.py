"""Proxmox Health Report Generator

Erstellt einen wöchentlichen HTML-Health-Report mit VM-Status,
Ressourcenauslastung und Backup-Übersicht.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_pvesh(endpoint: str) -> dict:
    """Führt einen pvesh-Befehl aus und gibt JSON zurück."""
    try:
        result = subprocess.run(
            ["pvesh", "get", endpoint, "--output-format", "json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"WARNUNG: pvesh {endpoint} fehlgeschlagen: {result.stderr}", file=sys.stderr)
            return {}
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"WARNUNG: {e}", file=sys.stderr)
        return {}


def generate_html_report(output_path: str = "health-report.html") -> str:
    """Erstellt einen HTML-Health-Report.

    Args:
        output_path: Pfad für die Ausgabedatei

    Returns:
        Pfad zur generierten HTML-Datei
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Daten sammeln
    nodes = run_pvesh("/nodes")
    resources = run_pvesh("/cluster/resources?type=vm")

    # VM-Zeilen aufbauen
    vm_rows = ""
    vm_success = 0
    vm_stopped = 0

    for vm in resources:
        vmid = vm.get("vmid", "?")
        name = vm.get("name", "unbekannt")
        status = vm.get("status", "?")
        cpu = vm.get("cpu", 0) * 100
        maxmem = vm.get("maxmem", 1)
        mem = vm.get("mem", 0)
        mem_pct = (mem / maxmem * 100) if maxmem > 0 else 0
        maxdisk = vm.get("maxdisk", 1)
        disk = vm.get("disk", 0)
        disk_pct = (disk / maxdisk * 100) if maxdisk > 0 else 0
        uptime = vm.get("uptime", 0)
        hours = int(uptime // 3600) if uptime else 0

        status_color = "#22c55e" if status == "running" else "#ef4444"
        status_text = "Laufend" if status == "running" else "Gestoppt"
        if status == "running":
            vm_success += 1
        else:
            vm_stopped += 1

        cpu_color = "#ef4444" if cpu > 90 else "#f59e0b" if cpu > 70 else "#22c55e"
        mem_color = "#ef4444" if mem_pct > 90 else "#f59e0b" if mem_pct > 70 else "#22c55e"

        vm_rows += f"""
        <tr>
            <td>{vmid}</td>
            <td>{name}</td>
            <td><span style="color:{status_color}; font-weight:bold;">{status_text}</span></td>
            <td>{hours}h</td>
            <td><span style="color:{cpu_color}">{cpu:.1f}%</span></td>
            <td><span style="color:{mem_color}">{mem_pct:.1f}%</span></td>
            <td>{disk_pct:.1f}%</td>
        </tr>"""

    # HTML zusammenbauen
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Proxmox Health Report — {now}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; background: #f8fafc; color: #1e293b; }}
        h1 {{ color: #0f172a; }}
        h2 {{ color: #334155; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        th {{ background: #1e293b; color: white; padding: 12px 15px; text-align: left; }}
        td {{ padding: 10px 15px; border-bottom: 1px solid #e2e8f0; }}
        tr:hover {{ background: #f1f5f9; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); flex: 1; }}
        .card h3 {{ margin: 0 0 10px; color: #64748b; font-size: 14px; text-transform: uppercase; }}
        .card .value {{ font-size: 28px; font-weight: bold; }}
        .green {{ color: #22c55e; }}
        .red {{ color: #ef4444; }}
        .blue {{ color: #3b82f6; }}
        .footer {{ margin-top: 30px; color: #94a3b8; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>📊 Proxmox Health Report</h1>
    <p>Erstellt: {now}</p>

    <div class="summary">
        <div class="card">
            <h3>Knoten</h3>
            <div class="value blue">{len(nodes)}</div>
        </div>
        <div class="card">
            <h3>Laufend</h3>
            <div class="value green">{vm_success}</div>
        </div>
        <div class="card">
            <h3>Gestoppt</h3>
            <div class="value red">{vm_stopped}</div>
        </div>
        <div class="card">
            <h3>Gesamt</h3>
            <div class="value">{vm_success + vm_stopped}</div>
        </div>
    </div>

    <h2>VM & Container Übersicht</h2>
    <table>
        <tr><th>ID</th><th>Name</th><th>Status</th><th>Uptime</th><th>CPU</th><th>RAM</th><th>Disk</th></tr>
        {vm_rows if vm_rows else "<tr><td colspan='7'>Keine VMs gefunden</td></tr>"}
    </table>

    <div class="footer">
        Generiert von Proxmox Automation Toolkit — proxmox-automation-toolkit
    </div>
</body>
</html>"""

    # Datei speichern
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print(f"Report gespeichert: {path.absolute()}")
    return str(path.absolute())


def main():
    parser = argparse.ArgumentParser(description="Proxmox Health Report erstellen")
    parser.add_argument("--output", "-o", type=str, default="health-report.html", help="Ausgabedatei")
    args = parser.parse_args()

    generate_html_report(args.output)


if __name__ == "__main__":
    main()
