"""
Gestion des accès Tailscale ACL avec ajout/révocation dynamique via API
Suivi des accès temporaires via base de données (models.AccessRequest)
"""

import json
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os


class TailscaleACLManager:
    """Gère les modifications du fichier ACL Tailscale via l'API"""

    def __init__(self, api_token: str, tailnet: str):
        """
        Initialise le gestionnaire ACL

        Args:
            api_token: Token API Tailscale
            tailnet: Identifiant du tailnet (ex: "example.com")
        """
        self.api_token = api_token
        self.tailnet = tailnet
        self.api_base_url = f"https://api.tailscale.com/api/v2/tailnet/{tailnet}"
        self.acl_data = None
        self.load_acl()

    def load_acl(self) -> Dict:
        """Charge l'ACL depuis l'API Tailscale"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_token}'
            }
            response = requests.get(
                f"{self.api_base_url}/acl",
                headers=headers
            )
            response.raise_for_status()

            # Certaines ACL sont en style HuJSON (virgules finales/commentaires).
            data = self._parse_acl_payload(response.text)
            print(f"ACL chargée depuis l'API: {data}")

            # L'API retourne { "ssh": [...] }
            self.acl_data = data
            return self.acl_data
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erreur lors de la lecture de l'ACL de l'API: {e}")
   
   
    def _parse_acl_payload(self, raw_payload: str) -> Dict:
        """Parse un payload ACL en acceptant les virgules finales et commentaires."""
        try:
            return json.loads(raw_payload)
        except json.JSONDecodeError:
            pass

        # Supprime les commentaires // et /* */ courants dans le HuJSON.
        without_comments = re.sub(r"/\*.*?\*/", "", raw_payload, flags=re.DOTALL)
        without_comments = re.sub(r"^\s*//.*$", "", without_comments, flags=re.MULTILINE)

        # Supprime les virgules finales avant } ou ]
        cleaned = re.sub(r",(\s*[}\]])", r"\1", without_comments)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise Exception(f"Format ACL invalide (JSON/HuJSON): {e}")

    def save_acl(self) -> bool:
        """Envoie les modifications de l'ACL via l'API Tailscale"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            # L'API attend { "ssh": [...] }
            response = requests.post(
                f"{self.api_base_url}/acl",
                headers=headers,
                json=self.acl_data
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la sauvegarde via l'API: {e}")
            return False

    def _get_ssh_list(self) -> List[Dict]:
        """Retourne la liste des ssh"""
        return self.acl_data.get('ssh', [])

    def _set_ssh_list(self, ssh_list: List[Dict]):
        """Met à jour la liste des ssh"""
        self.acl_data['ssh'] = ssh_list
    
    def _get_gtr_list(self) -> List[Dict]:
        """Retourne la liste des gtr"""
        return self.acl_data.get('grants', [])

    def _set_gtr_list(self, gtr_list: List[Dict]):
        """Met à jour la liste des gtr"""
        self.acl_data['grants'] = gtr_list

    def _validate_machine_tag(self, machine_tag: str) -> bool:
        """
        Valide le format du tag machine

        Args:
            machine_tag: Tag de la machine (ex: "tag:machine-1")

        Returns:
            bool: True si valide
        """
        if not isinstance(machine_tag, str):
            return False
        return machine_tag.startswith("tag:machine-") and len(machine_tag) > len("tag:machine-")

    def grant_access(self, user_email: str, machine_tag: str) -> Tuple[bool, str]:
        """
        Accorde l'accès d'un utilisateur à une machine via l'ACL

        Args:
            user_email: Email de l'utilisateur (ex: "test@example.com")
            machine_tag: Tag de la machine (ex: "tag:machine-1")

        Returns:
            tuple: (succès, message)
        """
        # Valider le tag
        if not self._validate_machine_tag(machine_tag):
            return False, f"Tag invalid: {machine_tag}"

        # Vérifier si l'accès existe déjà
        if self._access_exists(user_email, machine_tag):
            return False, f"Accès déjà existant pour {user_email} à {machine_tag}"

        # Créer une règle ACL simple (sans métadonnées, suivi en BD seulement)
        acl_entry = {
            "action": "accept",
            "src": [user_email],
            "dst": [f"{machine_tag}"],
            "users":  ["root", "autogroup:nonroot"]

        }
        gtr_entry = {
            "src": [user_email],
            "dst": [f"{machine_tag}"],
            "ip": ["*"],
        }

        acl_list = self._get_ssh_list()
        acl_list.append(acl_entry)
        self._set_ssh_list(acl_list)

        gtr_list = self._get_gtr_list()
        gtr_list.append(gtr_entry)
        self._set_gtr_list(gtr_list)

        if self.save_acl():
            return True, f"Accès accordé à {user_email} pour {machine_tag}"
        else:
            # Restaurer l'état précédent
            acl_list.pop()
            self._set_ssh_list(acl_list)
            return False, "Erreur lors de la sauvegarde via l'API"

    def revoke_access(self, user_email: str, machine_tag: str) -> Tuple[bool, str]:
        """
        Révoque l'accès d'un utilisateur à une machine

        Args:
            user_email: Email de l'utilisateur
            machine_tag: Tag de la machine

        Returns:
            tuple: (succès, message)
        """
        ssh_list = self._get_ssh_list()
        initial_len = len(ssh_list)

        # Chercher les règles ACL correspondantes
        filtered_list_ssh = [
            entry for entry in ssh_list
            if not (user_email in entry.get('src', []) and
                   machine_tag in entry.get('dst', []))
        ]
        filtered_list_gtr = [
            entry for entry in self._get_gtr_list()
            if not (user_email in entry.get('src', []) and
                   machine_tag in entry.get('dst', []))
        ]

        if len(filtered_list_ssh) == initial_len:
            return False, f"Aucun accès trouvé pour {user_email} à {machine_tag}"

        self._set_ssh_list(filtered_list_ssh)
        self._set_gtr_list(filtered_list_gtr)
        if self.save_acl():
            removed = initial_len - len(filtered_list_ssh)
            return True, f"Accès révoqué pour {user_email} à {machine_tag} ({removed} entrées supprimées)"
        else:
            self._set_ssh_list(ssh_list)  # Restaurer
            return False, "Erreur lors de la sauvegarde via l'API"

    def _access_exists(self, user_email: str, machine_tag: str) -> bool:
        """Vérifie si un accès existe déjà dans les ACL"""
        for entry in self._get_ssh_list():
            if (user_email in entry.get('src', []) and
                machine_tag in entry.get('dst', [])):
                return True
        return False

    def list_all_access(self) -> List[Dict]:
        """Liste tous les accès depuis les ACL"""
        access_list = []

        for entry in self._get_ssh_list():
            src = entry.get('src', [None])[0]
            dst = entry.get('dst', [None])[0]
            if src and dst:
                access_list.append({
                    'user': src,
                    'machine': dst,
                    'action': entry.get('action', 'accept')
                })

        return access_list

