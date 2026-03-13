# IAM Dashboard avec Tailscale & Authentik

Dashboard IAM moderne avec gestion des demandes d'accès aux serveurs Tailscale.

## Fonctionnalités

✅ **Authentification OAuth2/OIDC** via Authentik
✅ **API Tailscale** pour récupérer les appareils et utilisateurs
✅ **Dashboard Utilisateur** avec filtrage par tags
✅ **Demandes d'Accès** aux serveurs (3 jours max)
✅ **Dashboard Admin** pour approuver/rejeter les demandes
✅ **Cron Job** pour expirer les accès automatiquement
✅ **Menu Conditionnel** selon les groupes d'utilisateurs

## Installation

### 1. Prérequis

- Python 3.8+
- PostgreSQL 12+
- Token API Tailscale
- Configuration Authentik

### 2. Installation des dépendances

```bash
pip install -r requirements.txt
```

### 3. Configuration des variables d'environnement

```bash
cp .env.example .env
# Éditez .env avec vos paramètres
```

**Variables requises:**
- `TAILSCALE_API_TOKEN` - Token Tailscale (https://tailscale.com/admin/settings/personal/keys)
- `TAILSCALE_TAILNET` - Votre tailnet (ex: "example.com")
- `DATABASE_URL` - URL PostgreSQL
- `AUTHENTIK_CLIENT_ID` et `AUTHENTIK_CLIENT_SECRET`

### 4. Initier la base de données

```bash
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('✅ Tables créées')"
```

### 5. Lancer l'application

```bash
python3 app.py
```

L'application sera accessible sur `http://localhost:5000`

## Configuration du Cron Job

Pour expirer automatiquement les accès après 3 jours :

```bash
crontab -e
```

Ajouter la ligne:
```
0 */6 * * * cd /home/mohammedsbihi/PFE/web-page && /usr/bin/python3 scripts/expire_access.py >> logs/cron.log 2>&1
```

## Architecture

```
web-page/
├── app.py                    # Application Flask principale
├── auth.py                   # Authentification Authentik
├── models.py                 # Modèles SQLAlchemy
├── requirements.txt          # Dépendances Python
├── .env.example             # Variables d'environnement exemple
├── templates/               # Templates Jinja2
│   ├── base.html
│   ├── admin_dashboard.html
│   ├── admin_access_requests.html
│   ├── user_dashboard.html
│   ├── login_authentik.html
│   └── profile.html
├── static/                  # CSS, JS, images
└── scripts/
    └── expire_access.py     # Script de cron job
```

## Flux de Demande d'Accès

1. **Utilisateur** demande l'accès à un serveur via le dashboard
2. **Demande enregistrée** dans PostgreSQL avec status "pending"
3. **Admin** voit la demande en attente et approuve/rejette
4. **Si approuvé**: Status = "approved", expires_at = maintenant + 3 jours
5. **Cron job** expire automatiquement les accès dépassant 3 jours

## Groupes & Tags

Mapping entre groupes Authentik et tags Tailscale:

```python
'dev' → 'tag:dev'
'prod' → 'tag:prod'
'admin' → 'tag:admin'
'read_users' → 'tag:user'
'Admins' → 'tag:admin'
```

## API Endpoints

### Publics (Authentifiés)
- `GET /api/users` - Liste des utilisateurs Tailscale
- `GET /api/servers` - Liste des serveurs Tailscale
- `POST /api/request-access` - Demander l'accès à un serveur

### Admin seulement
- `GET /admin/access-requests` - Dashboard gestion demandes
- `GET /api/access-requests` - Liste des demandes (API)
- `POST /api/access-request/<id>/approve` - Approuver
- `POST /api/access-request/<id>/deny` - Rejeter

## Développement

### Lancer en mode debug

```bash
export FLASK_DEBUG=1
export FLASK_ENV=development
python3 app.py
```

### Tests

```bash
# À implémenter
pytest
```

## Dépannage

### Erreur de connexion à PostgreSQL
```
Vérifier: DATABASE_URL dans .env
Confirmer: Service PostgreSQL est actif
```

### API Tailscale timeout
```
Vérifier: TAILSCALE_API_TOKEN est valide
Confirmer: Connectivité internet
```

### Authentik non reconnu
```
Vérifier: AUTHENTIK_CLIENT_ID et SECRET
Confirmer: Redirect URI configuré dans Authentik
```

## TODO / À Faire

- [ ] Intégration Tailscale ACL (ajouter user aux groupes)
- [ ] Notifications email pour approvals
- [ ] Audit logging complet
- [ ] Tests unitaires
- [ ] Documentation API
- [ ] UI mobile responsif
- [ ] Pagination pour grandes listes

## Licence

Privé - PFE

## Support

Mohammed Sbihi - mohammed.sbihi@sbihi.tech
