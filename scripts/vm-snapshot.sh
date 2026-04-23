#!/usr/bin/env bash
# =============================================================================
# Proxmox VM Snapshot Script
# Erstellt einen Snapshot vor Updates und räumt alte Snapshots auf
# =============================================================================

set -euo pipefail

# Konfiguration
MAX_SNAPSHOTS="${MAX_SNAPSHOTS:-5}"
SNAPSHOT_PREFIX="pre-update"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $(date '+%H:%M:%S') $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }

usage() {
    cat << 'USAGE'
Verwendung: vm-snapshot.sh <VM-ID> [Snapshot-Name] [--cleanup-only]

Argumente:
  VM-ID          Proxmox VM/CT ID (z.B. 100)
  Snapshot-Name  Name des Snapshots (Standard: pre-update-YYYYMMDD-HHMMSS)
  --cleanup-only Nur alte Snapshots aufräumen, keinen neuen erstellen

Beispiele:
  vm-snapshot.sh 100
  vm-snapshot.sh 100 vor-kernel-update
  vm-snapshot.sh 100 --cleanup-only
USAGE
    exit 1
}

cleanup_snapshots() {
    local vmid="$1"
    log_info "Räume alte Snapshots auf (behalte maximal $MAX_SNAPSHOTS)..."

    local snapshots
    snapshots=$(pvesh get /nodes/$(hostname)/qemu/"$vmid"/snapshot --output-format json 2>/dev/null | \
        python3 -c "
import sys, json
snaps = json.load(sys.stdin)
prefix_snaps = [s['name'] for s in snaps if s['name'].startswith('$SNAPSHOT_PREFIX')]
prefix_snaps.sort()
# Behalte die neuesten MAX_SNAPSHOTS
for s in prefix_snaps[:-$MAX_SNAPSHOTS]:
    print(s)
" 2>/dev/null) || true

    if [[ -z "$snapshots" ]]; then
        log_info "Keine Snapshots zum Aufräumen."
        return
    fi

    while IFS= read -r snap_name; do
        [[ -z "$snap_name" ]] && continue
        log_info "Lösche Snapshot: $snap_name"
        if pvesh delete /nodes/$(hostname)/qemu/"$vmid"/snapshot/"$snap_name" 2>/dev/null; then
            log_info "Snapshot '$snap_name' gelöscht."
        else
            log_warn "Konnte Snapshot '$snap_name' nicht löschen (möglicherweise Container statt VM)."
        fi
    done <<< "$snapshots"
}

create_snapshot() {
    local vmid="$1"
    local snap_name="$2"

    # Prüfe ob VM/CT existiert
    if ! pvesh get /nodes/$(hostname)/qemu/"$vmid"/status/current &>/dev/null; then
        # Versuche Container
        if ! pvesh get /nodes/$(hostname)/lxc/"$vmid"/status/current &>/dev/null; then
            log_error "VM/CT mit ID $vmid nicht gefunden."
            exit 1
        fi
        log_info "Erstelle Snapshot für Container $vmid..."
        pvesh create /nodes/$(hostname)/lxc/"$vmid"/snapshot --snapname "$snap_name" 2>/dev/null || {
            log_error "Snapshot-Erstellung fehlgeschlagen."
            exit 1
        }
    else
        log_info "Erstelle Snapshot für VM $vmid..."
        pvesh create /nodes/$(hostname)/qemu/"$vmid"/snapshot --snapname "$snap_name" --vmstate 0 2>/dev/null || {
            log_error "Snapshot-Erstellung fehlgeschlagen."
            exit 1
        }
    fi

    log_info "Snapshot '$snap_name' für VM/CT $vmid erstellt."
}

# === Hauptprogramm ===

if [[ $# -lt 1 ]]; then
    usage
fi

VMID="$1"
if ! [[ "$VMID" =~ ^[0-9]+$ ]]; then
    log_error "Ungültige VM-ID: $VMID"
    exit 1
fi

if [[ "${2:-}" == "--cleanup-only" ]]; then
    cleanup_snapshots "$VMID"
    exit 0
fi

SNAP_NAME="${2:-${SNAPSHOT_PREFIX}-$(date '+%Y%m%d-%H%M%S')}"

create_snapshot "$VMID" "$SNAP_NAME"
cleanup_snapshots "$VMID"
