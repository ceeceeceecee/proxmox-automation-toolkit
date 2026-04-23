# Proxmox API-Token einrichten

## Schritt für Schritt Anleitung

### 1. API-Token erstellen

1. Proxmox Web-UI öffnen
2. **Datacenter** → **Permissions** → **API Tokens**
3. Klick auf **Add**
4. Folgende Einstellungen:
   - **User:** `root@pam` (oder ein dedizierter Benutzer)
   - **Token ID:** `automation` (oder anderer Name)
   - **Privilege Separation:** Deaktiviert (für einfache Nutzung)

5. **Create** klicken
6. **WICHTIG:** Das Secret kopieren und sicher aufbewahren! Es wird nur einmal angezeigt.

### 2. Berechtigungen vergeben (Least Privilege)

Erstelle einen dedizierten Benutzer statt Root zu verwenden:

```bash
# Benutzer erstellen
pvesh create /access/users --userid toolkit@pve --comment "Automatisierung"

# Rolle erstellen (minimale Berechtigungen)
pvesh create /access/roles --roleid ToolkitRole --privs "VM.Monitor,VM.Snapshot,VM.Snapshot.Rollback,VM.PowerMgmt"

# Rolle dem Benutzer zuweisen
pvesh create /access/acl --path / --users toolkit@pve --roles ToolkitRole

# API-Token für diesen Benutzer erstellen
pvesh create /access/users/toolkit@pve/token --id automation
```

### 3. Token in Konfiguration eintragen

```yaml
# config/settings.yaml
proxmox:
  host: "192.168.1.10"
  api_token_id: "toolkit@pve!automation"
  api_token_secret: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  verify_ssl: false
```

### 4. Verbindung testen

```bash
# Mit pvesh
pvesh get /nodes --tokenid toolkit@pve!automation --token-secret YOUR_SECRET

# Mit Python
python3 -c "
from proxmox_api import ProxmoxAPI
api = ProxmoxAPI('192.168.1.10', 'toolkit@pve!automation', 'YOUR_SECRET', verify_ssl=False)
print(api.get_nodes())
"
```

## Sicherheitstipps

- ** Niemals** Root-Passwort in Skripten verwenden
- ** Least Privilege:** Nur benötigte Berechtigungen vergeben
- ** Token rotieren:** Regelmäßig neue Tokens erstellen
- ** SSL:** In Produktion gültige Zertifikate verwenden
- ** Firewall:** API-Zugang nur von vertrauenswürdigen IPs erlauben
- ** Logging:** API-Zugriffe in Proxmox überwachen (Datacenter → Logs)
