# Proxmox Automation Toolkit

> Bash & Python Scripts für Proxmox VE Automatisierung — Backups, VM-Management, Monitoring, Deployment
> Bash & Python scripts for Proxmox VE automation: backups, VM management, monitoring, deployment

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ![Python](https://img.shields.io/badge/Python-3.10+-green.svg) ![Bash](https://img.shields.io/badge/Bash-5.0+-4EAA25.svg)

## Architektur

```
+-------------------+     +------------------+     +------------------+
|   Cron / systemd  | --> |  Bash Scripts    | --> |  Proxmox VE API  |
+-------------------+     +------------------+     +------------------+
                                  |
                                  v
                          +------------------+
                          | Python Scripts    |
                          | (pvesh / API)     |
                          +------------------+
                                  |
                                  v
                          +------------------+
                          | Benachrichtigung  |
                          | (Mail / Telegram) |
                          +------------------+
```

## Script-Übersicht

| Script | Sprache | Beschreibung |
|--------|---------|-------------|
| `scripts/backup-manager.sh` | Bash | Automatisches Backup aller VMs/CTs mit Retention |
| `scripts/vm-snapshot.sh` | Bash | Snapshot vor Updates erstellen |
| `scripts/resource-monitor.sh` | Bash | CPU/RAM/Disk-Überwachung aller VMs |
| `python/proxmox_api.py` | Python | API-Wrapper-Klasse für Proxmox |
| `python/deploy_ct.py` | Python | LXC Container automatisiert deployen |
| `python/health_report.py` | Python | Wöchentlicher HTML-Health-Report |

## Voraussetzungen

- Proxmox VE 7.x oder neuer
- Bash 5.0+
- Python 3.10+ (für Python-Scripte)
- `pvesh` CLI-Tool (auf dem Proxmox-Host)
- API-Token mit entsprechenden Berechtigungen

## Sicherheitshinweise

**API-Token statt Passwort!** Erstelle einen dedizierten API-Token mit minimalen Berechtigungen:

1. Proxmox Web-UI → Datacenter → Permissions → API Tokens
2. Neuen Token erstellen, nur benötigte Rechte vergeben
3. Token in `config/settings.yaml` eintragen
4. ** Niemals** Root-Passwort in Skripten speichern!

Siehe [docs/proxmox-api-setup.md](docs/proxmox-api-setup.md) für Details.

## Schnellstart

```bash
git clone https://github.com/ceeceeceecee/proxmox-automation-toolkit.git
cd proxmox-automation-toolkit

# Konfiguration anpassen
cp config/settings.example.yaml config/settings.yaml

# Backup-Script testen (Dry-Run)
bash scripts/backup-manager.sh --dry-run

# Cron-Einträge ansehen
cat cron/crontab.example
```

## Lizenz

MIT — siehe [LICENSE](LICENSE)
