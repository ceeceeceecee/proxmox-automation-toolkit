#!/usr/bin/env bash
# =============================================================================
# Proxmox Resource Monitor
# Überwacht CPU, RAM und Disk aller VMs und sendet Alerts bei Schwellenwerten
# =============================================================================

set -euo pipefail

# Schwellenwerte (in Prozent)
CPU_ALERT="${CPU_ALERT:-90}"
RAM_ALERT="${RAM_ALERT:-90}"
DISK_ALERT="${DISK_ALERT:-85}"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ALERT]${NC} $*"; }

# Prüfe pvesh
if ! command -v pvesh &>/dev/null; then
    echo "Fehler: pvesh nicht gefunden. Script muss auf einem Proxmox-Host laufen."
    exit 1
fi

echo "============================================================"
echo "  Proxmox Resource Monitor — $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
printf "%-8s %-20s %8s %8s %10s\n" "ID" "NAME" "CPU(%)" "RAM(%)" "DISK(%)"
echo "------------------------------------------------------------"

alerts=""

# Alle VMs/CTs abrufen
while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    vmid=$(echo "$line" | cut -d: -f1)
    name=$(echo "$line" | cut -d: -f2-)
    vmtype=$(echo "$line" | cut -d: -f3)

    # Ressourcen abrufen
    if [[ "$vmtype" == "qemu" ]]; then
        status_json=$(pvesh get /nodes/$(hostname)/qemu/"$vmid"/status/current --output-format json 2>/dev/null || echo '{}')
    else
        status_json=$(pvesh get /nodes/$(hostname)/lxc/"$vmid"/status/current --output-format json 2>/dev/null || echo '{}')
    fi

    cpu=$(echo "$status_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d.get(\"cpu\",0)*100:.1f}')" 2>/dev/null || echo "N/A")
    mem=$(echo "$status_json" | python3 -c "
import sys,json
d=json.load(sys.stdin)
used=d.get('mem',0); total=d.get('maxmem',1)
print(f'{used/total*100:.1f}' if total > 0 else 'N/A')
" 2>/dev/null || echo "N/A")
    disk=$(echo "$status_json" | python3 -c "
import sys,json
d=json.load(sys.stdin)
used=d.get('disk',0); total=d.get('maxdisk',1)
print(f'{used/total*100:.1f}' if total > 0 else 'N/A')
" 2>/dev/null || echo "N/A")

    # Prüfe Schwellenwerte
    warning=""
    cpu_num=$(echo "$cpu" | grep -oE '[0-9.]+' || echo "0")
    mem_num=$(echo "$mem" | grep -oE '[0-9.]+' || echo "0")
    disk_num=$(echo "$disk" | grep -oE '[0-9.]+' || echo "0")

    if (( $(echo "$cpu_num >= $CPU_ALERT" | bc -l 2>/dev/null || echo 0) )); then
        warning="${warning} CPU!"
    fi
    if (( $(echo "$mem_num >= $RAM_ALERT" | bc -l 2>/dev/null || echo 0) )); then
        warning="${warning} RAM!"
    fi
    if (( $(echo "$disk_num >= $DISK_ALERT" | bc -l 2>/dev/null || echo 0) )); then
        warning="${warning} DISK!"
    fi

    if [[ -n "$warning" ]]; then
        printf "${RED}%-8s %-20s %8s %8s %10s${NC}  %s\n" "$vmid" "${name:0:20}" "$cpu" "$mem" "$disk" "$warning"
        alerts="${alerts}⚠️ $name ($vmid):$warning\n"
    else
        printf "%-8s %-20s %8s %8s %10s\n" "$vmid" "${name:0:20}" "$cpu" "$mem" "$disk"
    fi

done < <(pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)
for d in data:
    print(f\"{d.get('vmid','')}:\" + d.get('name','?') + ':' + d.get('type','?'))
" 2>/dev/null || true)

echo "============================================================"

# Alerts ausgeben
if [[ -n "$alerts" ]]; then
    echo -e "\n${RED}ALERTS:${NC}"
    echo -e "$alerts"
    exit 1
else
    echo -e "\n${GREEN}Alle Ressourcen im Normbereich.${NC}"
    exit 0
fi
