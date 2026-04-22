#!/bin/bash
set -e

# Sécurité : Vérification du mot de passe
if [ -z "${SSH_PASSWORD:-}" ]; then
  echo "Erreur: variable SSH_PASSWORD non définie"
  exit 1
fi
echo "${SSH_USER}:${SSH_PASSWORD}" | chpasswd

# Logging : Configuration de rsyslog (sans kernel logs)
sed -i '/imklog/s/^/#/' /etc/rsyslog.conf
echo "auth,authpriv.* /app/logs/security_audit.log" > /etc/rsyslog.d/50-default.conf
touch /app/logs/security_audit.log
chmod 640 /app/logs/security_audit.log
chown syslog:adm /app/logs/security_audit.log 2>/dev/null || chown root:root /app/logs/security_audit.log


if [ ! -x /var/ossec/bin/wazuh-control ]; then
  echo "Erreur: wazuh-agent n'est pas installé dans l'image."
  exit 1
fi
	

echo "Configuration de l'agent Wazuh pour se connecter au manager..."
sed -i 's/<address>.*<\/address>/<address>wazuh.manager<\/address>/' /var/ossec/etc/ossec.conf
/var/ossec/bin/wazuh-control restart


