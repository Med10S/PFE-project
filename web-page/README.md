# IAM Web App + Authentik + Tailscale ACL

Application Flask pour gérer l'accès aux machines Tailscale avec:
- Authentification OAuth2/OIDC via Authentik
- Gestion des demandes d'acces en base (PostgreSQL)
- Workflow d'approbation/revocation ACL via `ACL_work`
- Expiration automatique des acces approuves (cron)

## Fonctionnalites principales

### 1) Authentification et autorisation
- Login via Authentik (`/login`, `/auth/callback`, `/logout`)
- Session utilisateur stockee cote Flask
- Roles/groupes valides par decorators (`require_login`, `require_permission`, `in_groupe`)

### 2) Logique d'acces machine (nouvelle logique)
Un utilisateur peut acceder a une machine si au moins une condition est vraie:
- Il partage un tag avec la machine (tag utilisateur vs tag device)
- Il possede une demande `approved` active en base pour cette machine (ACL temporaire)

Cette logique est appliquee dans le dashboard utilisateur.

### 3) Demandes d'acces (DB)
Table `access_requests` (modele `AccessRequest`):
- `pending`, `approved`, `denied`, `expired`
- `tailscale_tag`, `approved_by`, `approved_at`, `expires_at`, `acl_applied`

Flux:
- User -> `POST /api/request-access`
- Admin -> `POST /api/access-request/<id>/approve` ou `/deny`
- Tache maintenance -> expiration/revocation

### 4) Blocage "pending" cote API + UI
Si l'utilisateur a deja une demande `pending`:
- API refuse une nouvelle demande (`400`)
- Bouton "Demander Acces" desactive dans le dashboard utilisateur

### 5) Timer des acces approuves
Le dashboard utilisateur affiche les demandes `approved` actives avec:
- machine
- tag ACL
- date d'approbation
- temps restant (compteur live)

## Groupes et permissions

### Groupes utilises
- `authentik Admins`: acces administration des demandes
- `dev`: acces dashboard utilisateur

### Permissions OAuth (claims)
- `users:read`
- `users:update`
- `servers:manage`

## ACL_work (integration Tailscale)

Dossier: `ACL_work/`
- `tailscale_acl_api.py`: orchestration workflow ACL <-> DB
- `tailscale_acl_manager.py`: lecture/modification ACL Tailscale via API
- `tests/examples_integration.py`: exemple de bout en bout

Fonctions cle:
- `approve_access_request(...)`
- `revoke_access_request(...)`
- `cleanup_expired_requests(...)`

## Cron job (expiration des droits)

Script: `scripts/expire_access.py`

Exemple cron (toutes les 6h):

```cron
0 */6 * * * cd /chemin/vers/web-page && docker exec iam_web python3 scripts/expire_access.py >> /chemin/vers/web-page/logs/cron.log 2>&1
```

## Installation automatique (nouveau script)

Script ajoute: `scripts/install_app.sh`

Ce script:
- verifie les prerequis (`python3`, `docker`)
- verifie les variables obligatoires de `.env`
- si une variable est absente/vide, il demande la saisie interactive
- synchronise les aliases DB (`DB_*`) pour les scripts de maintenance
- installe les dependances Python dans `.venv`
- demarre `docker compose`
- initialise les tables SQLAlchemy
- propose d'ajouter automatiquement le cron job

### Lancer l'installation

```bash
cd /home/mohammedsbihi/PFE/web-page
./scripts/install_app.sh
```

## Variables d'environnement obligatoires

Le script valide ces variables:
- `AUTHENTIK_CLIENT_ID`
- `AUTHENTIK_CLIENT_SECRET`
- `AUTHENTIK_BASE_URL`
- `AUTHENTIK_REDIRECT_URI`
- `AUTHENTIK_AUTHORIZATION_URL`
- `AUTHENTIK_TOKEN_URL`
- `AUTHENTIK_USERINFO_URL`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `TAILSCALE_API_TOKEN`
- `TAILSCALE_TAILNET`
- `SECRET_KEY`

## Endpoints utiles

### UI
- `GET /admin/dashboard`
- `GET /user/dashboard`
- `GET /admin/access-requests`

### API
- `POST /api/request-access`
- `POST /api/access-request/<id>/approve`
- `POST /api/access-request/<id>/deny`
- `GET /api/access-requests`
- `POST /api/refresh-token`

## Roadmap de mise en place (recommandee)

### Phase 1 - Infrastructure
1. Configurer `.env` (Authentik, DB, Tailscale)
2. Lancer `./scripts/install_app.sh`
3. Verifier les conteneurs `iam_db` et `iam_web`

### Phase 2 - Authentik
1. Creer provider OAuth2/OIDC
2. Configurer redirect URI
3. Verifier les claims (`groups`, `permissions`, `email`)
4. Mapper les utilisateurs dans les groupes attendus (`authentik Admins`, `dev`)

### Phase 3 - ACL et workflow
1. Verifier `TAILSCALE_API_TOKEN` et `TAILSCALE_TAILNET`
2. Tester approbation/revocation via page admin
3. Verifier mise a jour de `access_requests` et application ACL

### Phase 4 - Maintenance
1. Activer cron d'expiration
2. Verifier les logs d'expiration
3. Valider la coherence des statuts (`approved` -> `expired`)

### Phase 5 - Production hardening
1. Supprimer tous les secrets hardcodes
2. Activer HTTPS bout-en-bout
3. Ajouter Flask-Migrate/Alembic pour les migrations DB
4. Ajouter monitoring, alerting, backup DB
5. Mettre des tests automatiques (API + UI)

## Commandes utiles

```bash
# Logs application
cd /home/mohammedsbihi/PFE/web-page
docker logs -f iam_web

# Etat des services
cd /home/mohammedsbihi/PFE/web-page
docker compose ps

# Lancer le script d'expiration manuellement
cd /home/mohammedsbihi/PFE/web-page
docker exec iam_web python3 scripts/expire_access.py
```

## Notes importantes
- `db.create_all()` ne remplace pas un vrai systeme de migration. Pour la prod, utiliser Alembic.
- Le workflow ACL depend de la disponibilite de l'API Tailscale et de la validite des tags machines.
- En cas de demande `pending`, la creation d'une nouvelle demande est volontairement bloquee.
