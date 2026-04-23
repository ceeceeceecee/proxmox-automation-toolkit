"""Proxmox API Wrapper

Bietet eine Python-Klasse zur Interaktion mit der Proxmox VE API.
Verwendet API-Token-Authentifizierung (kein Root-Passwort nötig).
"""

import requests
from typing import Optional


class ProxmoxAPI:
    """Wrapper für die Proxmox VE REST-API."""

    def __init__(
        self,
        host: str,
        api_token_id: str,
        api_token_secret: str,
        port: int = 8006,
        verify_ssl: bool = True,
    ):
        """
        Args:
            host: Proxmox-Hostname oder IP
            api_token_id: API-Token ID (z.B. "root@pam!automation")
            api_token_secret: API-Token Secret
            port: API-Port (Standard: 8006)
            verify_ssl: SSL-Zertifikat prüfen (bei Selbstsigniert: False)
        """
        self.base_url = f"https://{host}:{port}/api2/json"
        self.verify_ssl = verify_ssl

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"PVEAPIToken={api_token_id}={api_token_secret}",
        })

        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Führt eine API-Anfrage durch.

        Args:
            method: HTTP-Methode (GET, POST, PUT, DELETE)
            endpoint: API-Endpunkt (ohne Basis-URL)

        Returns:
            Antwortdaten als Dictionary.

        Raises:
            requests.exceptions.RequestException: Bei Netzwerkfehlern
            ValueError: Bei ungültigen API-Antworten
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(
                method, url, verify=self.verify_ssl, timeout=30, **kwargs
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(f"API-Fehler bei {endpoint}: {e}")
        except (ValueError, KeyError) as e:
            raise ValueError(f"Ungültige API-Antwort von {endpoint}: {e}")

    def get_nodes(self) -> list[dict]:
        """Gibt alle Proxmox-Nodes zurück."""
        return self._request("GET", "/nodes")

    def get_vms(self, node: str) -> list[dict]:
        """Gibt alle VMs eines Nodes zurück."""
        return self._request("GET", f"/nodes/{node}/qemu")

    def get_containers(self, node: str) -> list[dict]:
        """Gibt alle LXC-Container eines Nodes zurück."""
        return self._request("GET", f"/nodes/{node}/lxc")

    def get_vm_status(self, node: str, vmid: int) -> dict:
        """Gibt den Status einer VM zurück."""
        return self._request("GET", f"/nodes/{node}/qemu/{vmid}/status/current")

    def start_vm(self, node: str, vmid: int) -> dict:
        """Startet eine VM."""
        return self._request("POST", f"/nodes/{node}/qemu/{vmid}/status/start")

    def stop_vm(self, node: str, vmid: int) -> dict:
        """Stoppt eine VM."""
        return self._request("POST", f"/nodes/{node}/qemu/{vmid}/status/stop")

    def create_snapshot(self, node: str, vmid: int, name: str, description: str = "") -> dict:
        """Erstellt einen Snapshot einer VM."""
        return self._request(
            "POST",
            f"/nodes/{node}/qemu/{vmid}/snapshot",
            data={"snapname": name, "description": description},
        )

    def get_stats(self, node: str, vmid: int) -> dict:
        """Gibt aktuelle Ressourcenstatistiken einer VM zurück."""
        return self._request("GET", f"/nodes/{node}/qemu/{vmid}/status/current")

    def get_node_stats(self, node: str) -> dict:
        """Gibt Node-Ressourcenstatistiken zurück."""
        return self._request("GET", f"/nodes/{node}/status")
