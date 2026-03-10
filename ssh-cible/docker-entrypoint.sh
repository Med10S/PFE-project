#!/bin/bash
set -e

if [ -z "${SSH_PASSWORD:-}" ]; then
  echo "Erreur: variable SSH_PASSWORD non définie"
  exit 1
fi

echo "${SSH_USER}:${SSH_PASSWORD}" | chpasswd

mkdir -p /var/run/tailscale /var/lib/tailscale

if [ -n "${TAILSCALE_AUTHKEY:-}" ]; then
  tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &

  for _ in $(seq 1 20); do
    if tailscale --socket=/var/run/tailscale/tailscaled.sock status >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  tailscale --socket=/var/run/tailscale/tailscaled.sock up \
    --authkey="${TAILSCALE_AUTHKEY}" \
    --hostname="${TAILSCALE_HOSTNAME:-ssh-cible}"
else
  echo "TAILSCALE_AUTHKEY non défini: démarrage SSH sans Tailscale"
fi

exec /usr/sbin/sshd -D -e
