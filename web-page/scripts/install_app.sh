#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
VENV_DIR="$ROOT_DIR/.venv"

log() {
  echo "[install] $*"
}

error() {
  echo "[install][error] $*" >&2
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    error "Commande requise introuvable: $1"
    exit 1
  fi
}

trim_spaces() {
  local value="$1"
  value="${value#${value%%[![:space:]]*}}"
  value="${value%${value##*[![:space:]]}}"
  echo "$value"
}

escape_sed_replacement() {
  echo "$1" | sed -e 's/[&|]/\\&/g'
}

get_env_value() {
  local key="$1"
  if [[ ! -f "$ENV_FILE" ]]; then
    echo ""
    return
  fi

  local line
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    echo ""
    return
  fi

  local value="${line#*=}"
  value="$(trim_spaces "$value")"

  if [[ "${value:0:1}" == '"' && "${value: -1}" == '"' && ${#value} -ge 2 ]]; then
    value="${value:1:${#value}-2}"
  fi

  echo "$value"
}

set_env_value() {
  local key="$1"
  local value="$2"
  local escaped
  escaped="$(escape_sed_replacement "$value")"

  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${escaped}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi
}

ask_required_env() {
  local key="$1"
  local prompt="$2"
  local secret="${3:-false}"
  local current
  current="$(get_env_value "$key")"

  if [[ -n "$current" ]]; then
    log "${key} est déjà défini."
    return
  fi

  local input=""
  while [[ -z "$input" ]]; do
    if [[ "$secret" == "true" ]]; then
      read -rsp "${prompt}: " input
      echo
    else
      read -rp "${prompt}: " input
    fi
    input="$(trim_spaces "$input")"
    if [[ -z "$input" ]]; then
      echo "Valeur obligatoire pour ${key}."
    fi
  done

  set_env_value "$key" "$input"
}

ensure_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    log "Fichier .env introuvable, création d'un nouveau fichier."
    touch "$ENV_FILE"
  fi
}

sync_db_aliases_for_scripts() {
  local p_user p_pass p_host p_port p_db
  p_user="$(get_env_value "POSTGRES_USER")"
  p_pass="$(get_env_value "POSTGRES_PASSWORD")"
  p_host="$(get_env_value "POSTGRES_HOST")"
  p_port="$(get_env_value "POSTGRES_PORT")"
  p_db="$(get_env_value "POSTGRES_DB")"

  [[ -n "$p_user" ]] && set_env_value "DB_USER" "$p_user"
  [[ -n "$p_pass" ]] && set_env_value "DB_PASSWORD" "$p_pass"
  [[ -n "$p_host" ]] && set_env_value "DB_HOST" "$p_host"
  [[ -n "$p_port" ]] && set_env_value "DB_PORT" "$p_port"
  [[ -n "$p_db" ]] && set_env_value "DB_NAME" "$p_db"
}

install_python_deps() {
  log "Installation des dépendances Python..."
  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi

  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt"
}

ensure_authentik_network() {
  if ! docker network inspect authentik_network >/dev/null 2>&1; then
    log "Création du réseau Docker externe authentik_network..."
    docker network create authentik_network >/dev/null
  fi
}

start_stack() {
  log "Démarrage des conteneurs Docker..."
  (cd "$ROOT_DIR" && docker compose up -d --build)
}

create_tables() {
  log "Initialisation du schéma SQLAlchemy..."
  (cd "$ROOT_DIR" && docker compose exec -T web python3 -c "from app import app, db; ctx=app.app_context(); ctx.push(); db.create_all(); ctx.pop(); print('tables initialized')")
}


main() {
  require_cmd python3
  require_cmd docker
  require_cmd sed
  require_cmd grep

  ensure_env_file

  log "Vérification des variables .env obligatoires..."
  ask_required_env "AUTHENTIK_CLIENT_ID" "AUTHENTIK_CLIENT_ID"
  ask_required_env "AUTHENTIK_CLIENT_SECRET" "AUTHENTIK_CLIENT_SECRET" true
  ask_required_env "AUTHENTIK_BASE_URL" "AUTHENTIK_BASE_URL (ex: https://authentik.example.com)"
  ask_required_env "AUTHENTIK_REDIRECT_URI" "AUTHENTIK_REDIRECT_URI (ex: https://domain/auth/callback)"
  ask_required_env "AUTHENTIK_AUTHORIZATION_URL" "AUTHENTIK_AUTHORIZATION_URL"
  ask_required_env "AUTHENTIK_TOKEN_URL" "AUTHENTIK_TOKEN_URL"
  ask_required_env "AUTHENTIK_USERINFO_URL" "AUTHENTIK_USERINFO_URL"

  ask_required_env "POSTGRES_USER" "POSTGRES_USER"
  ask_required_env "POSTGRES_PASSWORD" "POSTGRES_PASSWORD" true
  ask_required_env "POSTGRES_HOST" "POSTGRES_HOST (ex: postgres)"
  ask_required_env "POSTGRES_PORT" "POSTGRES_PORT (ex: 5432)"
  ask_required_env "POSTGRES_DB" "POSTGRES_DB"
  ask_required_env "WEBFINGER_SUBJECT" "WEBFINGER_SUBJECT (ex: acct:mohammed.sbihi@sbihi.tech)"

  ask_required_env "TAILSCALE_API_TOKEN" "TAILSCALE_API_TOKEN" true
  ask_required_env "TAILSCALE_TAILNET" "TAILSCALE_TAILNET (ex: company.com)"
  ask_required_env "SECRET_KEY" "SECRET_KEY Flask" true

  sync_db_aliases_for_scripts

  install_python_deps
  ensure_authentik_network
  start_stack
  create_tables

  log "Installation terminée."
  log "Application: http://localhost:5000"
  log "Logs web: docker logs -f iam_web"
}

main "$@"
