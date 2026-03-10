#!/bin/bash
set -e

if [ -z "${SSH_PASSWORD:-}" ]; then
  echo "Erreur: variable SSH_PASSWORD non définie"
  exit 1
fi

echo "${SSH_USER}:${SSH_PASSWORD}" | chpasswd
exec /usr/sbin/sshd -D -e
