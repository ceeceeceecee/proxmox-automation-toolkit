#!/usr/bin/env bash
# =============================================================================
# Proxmox Backup Manager
# Automatisches Backup aller VMs und Container mit Retention-Policy
# =============================================================================

set -euo pipefail

# Konfiguration — Pfade zur Einstellungsdatei
CONFIG_FILE="${CONFIG_FILE:-/etc/proxmox-toolkit/settings.yaml}"
LOG_FILE="/var/log/proxmox-backup.log"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Hilfsfunktionen
# =============================================================================

log() {
    local level="$1"
    shift
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

log_info()  { log "INFO"  "$@"; }
log_warn()  { log "WARN"  "${YELLOW}$*${NC}"; }
log_error() { log "ERROR" "${RED}$*${NC}"; }
log_ok()    { log "OK"    "${GREEN}$*${NC}"; }

send_notification() {
    # Benachrichtigung per E-Mail oder Telegram (konfigurierbar)
    local subject="$1"
    local body="$2"

    # E-Mail (wenn mailx installiert)
    if command -v mailx &>/dev/null; then
        echo "$body" | mailx -s "$subject" "${EMAIL_RECIPIENT:-admin@example.com}" 2>/dev/null || true
    fi

    # Telegram (wenn TELEGRAM_BOT_TOKEN und TELEGRAM_CHAT_ID gesetzt)
    if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="$TELEGRAM_CHAT_ID" \
            -d text="$subject: $body" \
            -d parse_mode="Markdown" >/dev/null 2>&1 || true
    fi
}

cleanup_old_backups() {
    # Lösche Backups, die älter als RETENTION_DAYS sind
    log_info "Bereinige Backups älter als $RETENTION_DAYS Tage..."

    local deleted=0
    # vzdump speichert Backups standardmäßig unter /var/lib/vz/dump/
    if [[ -d /var/lib/vz/dump ]]; then
        while IFS= read -r -d '' file; do
            log_info "Lösche: $file"
            rm -f "$file"
            ((deleted++))
        done < <(find /var/lib/vz/dump -name "vzdump-*.vma.zst" -mtime +"$RETENTION_DAYS" -print0 2>/dev/null)
    fi

    log_ok "Bereinigung abgeschlossen: $deleted alte Backups gelöscht"
}

# =============================================================================
# Hauptfunktion
# =============================================================================

main() {
    local dry_run=false
    [[ "${1:-}" == "--dry-run" ]] && dry_run=true

    log_info "=== Proxmox Backup Manager gestartet ==="
    [[ "$dry_run" == true ]] && log_warn "DRY-RUN Modus — keine Backups werden erstellt"

    # Prüfe ob pvesh verfügbar ist
    if ! command -v pvesh &>/dev/null; then
        log_error "pvesh nicht gefunden. Script muss auf einem Proxmox-Host ausgeführt werden."
        exit 1
    fi

    # Alle VMs und Container auflisten
    local vms
    vms=$(pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | \
        python3 -c "import sys,json; [print(str(d.get('vmid','')) + ':' + d.get('name','unbekannt')) for d in json.load(sys.stdin)]" 2>/dev/null || true)

    if [[ -z "$vms" ]]; then
        log_warn "Keine VMs oder Container gefunden."
        send_notification "Proxmox Backup" "Keine VMs zum Sichern gefunden."
        exit 0
    fi

    local success=0
    local failed=0
    local errors=""

    # Jede VM/CT sichern
    while IFS=: read -r vmid name; do
        [[ -z "$vmid" ]] && continue

        log_info "Sichere VM/CT: $name (ID: $vmid)..."

        if [[ "$dry_run" == true ]]; then
            log_info "[DRY-RUN] vzdump $vmid --mode snapshot --compress zstd --storage local"
            ((success++))
            continue
        fi

        if vzdump "$vmid" --mode snapshot --compress zstd --storage local --quiet 2>>"$LOG_FILE"; then
            log_ok "Backup erfolgreich: $name ($vmid)"
            ((success++))
        else
            log_error "Backup fehlgeschlagen: $name ($vmid)"
            errors="${errors}- $name ($vmid)\n"
            ((failed++))
        fi
    done <<< "$vms"

    # Alte Backups aufräumen
    [[ "$dry_run" == false ]] && cleanup_old_backups

    # Zusammenfassung
    log_info "=== Backup abgeschlossen ==="
    log_info "Erfolgreich: $success | Fehlgeschlagen: $failed"

    # Benachrichtigung senden
    if [[ "$failed" -gt 0 ]]; then
        send_notification "⚠️ Proxmox Backup: $failed Fehler" "Erfolgreich: $success, Fehlgeschlagen: $failed\n\nFehlerhafte VMs:\n$errors"
    else
        send_notification "✅ Proxmox Backup erfolgreich" "$success VMs/CTs gesichert"
    fi

    exit "$failed"
}

main "$@"
