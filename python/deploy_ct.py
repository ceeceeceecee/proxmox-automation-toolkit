"""LXC Container Deployment

Automatisiertes Erstellen und Konfigurieren von LXC-Containern auf Proxmox VE.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Führt ein Shell-Kommando aus und gibt das Ergebnis zurück.

    Args:
        cmd: Auszuführendes Kommando als String
        check: Bei Fehler abbrechen (Standard: True)

    Returns:
        CompletedProcess-Objekt

    Raises:
        subprocess.CalledProcessError: Bei check=True und Exit-Code != 0
    """
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"  FEHLER: {result.stderr}")
        sys.exit(1)
    return result


def deploy_container(
    vmid: int,
    hostname: str,
    template: str = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
    storage: str = "local-lvm",
    rootfs_size: str = "8G",
    cpu_cores: int = 2,
    ram_mb: int = 2048,
    ip_address: str = "dhcp",
    gateway: str = "",
    ssh_public_key: str = "",
    start: bool = True,
) -> None:
    """Stellt einen LXC Container bereit.

    Args:
        vmid: Container-ID (100-999999999)
        hostname: Hostname des Containers
        template: Pfad zum Container-Template
        storage: Speicherort für Root-FS
        rootfs_size: Größe der Root-Partition
        cpu_cores: Anzahl CPU-Kerne
        ram_mb: Arbeitsspeicher in MB
        ip_address: IP-Adresse oder "dhcp"
        gateway: Gateway-IP (leer bei DHCP)
        ssh_public_key: SSH Public Key für root-Zugang
        start: Container nach Erstellung starten
    """
    print(f"\n🚀 Erstelle Container: {hostname} (ID: {vmid})")

    # Prüfe ob pvesh verfügbar ist
    try:
        run_command("which pvesh")
    except SystemExit:
        print("FEHLER: pvesh nicht gefunden. Script auf Proxmox-Host ausführen.")
        sys.exit(1)

    # Container erstellen
    print(f"\n📦 Template: {template}")
    create_cmd = (
        f"pvesh create /nodes/$(hostname)/lxc "
        f"--vmid {vmid} "
        f"--hostname {hostname} "
        f"--ostemplate '{template}' "
        f"--storage {storage} "
        f"--rootfs {storage}:{rootfs_size} "
        f"--cores {cpu_cores} "
        f"--memory {ram_mb}"
    )

    if ip_address != "dhcp":
        create_cmd += f" --net0 name=eth0,ip={ip_address},gw={gateway}"
    else:
        create_cmd += " --net0 name=eth0,ip=dhcp"

    if ssh_public_key:
        # SSH-Key aus Datei lesen falls Pfad
        key_path = Path(ssh_public_key)
        if key_path.exists():
            ssh_public_key = key_path.read_text().strip()
        create_cmd += f" --ssh-public-keys '{ssh_public_key}'"

    run_command(create_cmd)

    # Container starten
    if start:
        print(f"\n✅ Starte Container...")
        run_command(f"pvesh create /nodes/$(hostname)/lxc/{vmid}/status/start")
        print(f"\n🎉 Container '{hostname}' (ID: {vmid}) erfolgreich erstellt und gestartet!")
    else:
        print(f"\n🎉 Container '{hostname}' (ID: {vmid}) erfolgreich erstellt (nicht gestartet).")


def main():
    parser = argparse.ArgumentParser(
        description="LXC Container auf Proxmox VE bereitstellen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Minimal mit DHCP
  python deploy_ct.py --vmid 200 --hostname webserver

  # Mit statischer IP und SSH-Key
  python deploy_ct.py --vmid 201 --hostname db --ip 192.168.1.50 --gw 192.168.1.1 --ssh-key ~/.ssh/id_ed25519.pub

  # Mit benutzerdefiniertem Template
  python deploy_ct.py --vmid 202 --hostname monitoring --template local:vztmpl/debian-12.tar.zst
        """,
    )

    parser.add_argument("--vmid", type=int, required=True, help="Container-ID (100-999999999)")
    parser.add_argument("--hostname", type=str, required=True, help="Hostname")
    parser.add_argument("--template", type=str, default="local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst", help="Container-Template")
    parser.add_argument("--storage", type=str, default="local-lvm", help="Speicherort")
    parser.add_argument("--rootfs", type=str, default="8G", help="Root-Partition Größe")
    parser.add_argument("--cpu", type=int, default=2, help="CPU-Kerne")
    parser.add_argument("--ram", type=int, default=2048, help="RAM in MB")
    parser.add_argument("--ip", type=str, default="dhcp", help="IP-Adresse oder 'dhcp'")
    parser.add_argument("--gw", type=str, default="", help="Gateway-IP")
    parser.add_argument("--ssh-key", type=str, default="", help="SSH Public Key (Pfad oder Inhalt)")
    parser.add_argument("--no-start", action="store_true", help="Container nicht automatisch starten")

    args = parser.parse_args()

    deploy_container(
        vmid=args.vmid,
        hostname=args.hostname,
        template=args.template,
        storage=args.storage,
        rootfs_size=args.rootfs,
        cpu_cores=args.cpu,
        ram_mb=args.ram,
        ip_address=args.ip,
        gateway=args.gw,
        ssh_public_key=args.ssh_key,
        start=not args.no_start,
    )


if __name__ == "__main__":
    main()
