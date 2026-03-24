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
echo "auth,authpriv.* /var/log/auth.log" > /etc/rsyslog.d/50-default.conf
touch /var/log/auth.log
chmod 640 /var/log/auth.log
chown syslog:adm /var/log/auth.log 2>/dev/null || chown root:root /var/log/auth.log

# Audit : Injection de la traçabilité Tailscale dans le Bash
cat << 'EOF' >> /etc/bash.bashrc
# --- Système d'Audit Tailscale + Wazuh ---
shopt -s histappend
export HISTCONTROL=ignoredups:erasedups

# Fonction pour récupérer l'identité réelle via Tailscale
get_tailscale_user() {
  local ip="${SSH_CONNECTION%% *}"
  if [ -n "$ip" ]; then
    # On utilise ta commande validée avec jq
    local ts_user=$(tailscale whois --json "$ip" 2>/dev/null | jq -r .UserProfile.LoginName)
    echo "${ts_user:-unknown_ts_user}"
  else
    echo "local_exec"
  fi
}

# Enregistre CHAQUE commande avec l'email Tailscale dans auth.log
export PROMPT_COMMAND="history -a; TS_EMAIL=\$(get_tailscale_user); logger -p auth.info -t bash -i \"[\$TS_EMAIL from  \${SSH_CONNECTION%% *} using $(whoami)] \$(history 1 | sed 's/^[ ]*[0-9]*[ ]*//')\""
# -----------------------------------------
EOF

# Lancement des services
rm -f /run/rsyslogd.pid
/usr/sbin/rsyslogd
tailscaled &

sed -i 's/<address>.*<\/address>/<address>wazuh.manager<\/address>/' /var/ossec/etc/ossec.conf
/var/ossec/bin/wazuh-control restart


echo "Architecture sécurisée prête. Démarrage de SSH..."
exec /usr/sbin/sshd -D -e