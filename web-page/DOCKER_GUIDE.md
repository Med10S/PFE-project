# Guide de Déploiement avec Docker

## 🐳 Architecture Docker

```
┌─────────────────────────────────────┐
│      Docker Network (iam_network)   │
├─────────────────────────────────────┤
│                                     │
│            ┌──────────────────┐     │        
│            │   Flask Web      │     │        
│            │   (Port 5000)    │     │        
│            └────────┬─────────┘     │        
│                     │               │        
│                     │               │
│                     │               │
│              ┌──────▼──────┐        │
│              │ PostgreSQL  │        │
│              │ (Port 5432) │        │
│              └─────────────┘        │
│                                     │
└─────────────────────────────────────┘
```

## 📋 Prérequis

- **Docker** 20.10+
- **Docker Compose** 2.0+

### Installation

```bash
# Ubuntu/Debian
sudo apt-get install docker.io docker-compose

# macOS (via Homebrew)
brew install docker docker-compose

# Ou utiliser Docker Desktop
```

## 🚀 Démarrage Rapide

### 1. Préparer l'environnement

```bash
cd /home/mohammedsbihi/PFE

# Créer le fichier .env depuis l'exemple
cp web-page/.env.example web-page/.env

# Éditer avec vos valeurs
nano web-page/.env
```

**Valeurs à personnaliser dans `.env`:**
```env
# Tailscale (OBLIGATOIRE)
TAILSCALE_API_TOKEN=votre_token_api_tailscale
TAILSCALE_TAILNET=votre_tailnet

# PostgreSQL (Optionnel - utilise les defaults)
DB_USER=iam_user
DB_PASSWORD=change_me_to_very_long_secure_password
DB_NAME=iam_db

# Authentik (Vérifier les URLs)
AUTHENTIK_CLIENT_ID=...
AUTHENTIK_CLIENT_SECRET=...
AUTHENTIK_BASE_URL=https://authentik.sbihi.tech
```

### 2. Démarrer les conteneurs

```bash
# Mode production (fond)
docker-compose up -d

# Mode développement (logs visibles)
docker-compose up

# Avec PgAdmin pour déboguer (optionnel)
docker-compose --profile debug up -d
```

### 3. Vérifier le statut

```bash
# Voir les conteneurs en cours d'exécution
docker-compose ps

# Voir les logs
docker-compose logs -f web

# Tester la connexion
curl http://localhost:5000
```

### 4. Accéder à l'application

- **Web App:** http://localhost:5000
- **PgAdmin (debug):** http://localhost:5050
  - Email: admin@example.com (défaut)
  - Password: admin (défaut)

## ⚙️ Configuration Détaillée

### Variables d'Environnement

| Variable | Défaut | Description |
|----------|---------|-------------|
| `DB_USER` | `iam_user` | Utilisateur PostgreSQL |
| `DB_PASSWORD` | `iam_password_change_me` | Mot de passe PostgreSQL |
| `DB_HOST` | `postgres` | Host PostgreSQL (laissez postgres en Docker) |
| `DB_PORT` | `5432` | Port PostgreSQL |
| `DB_NAME` | `iam_db` | Nom de la base de données |
| `TAILSCALE_API_TOKEN` | - | **OBLIGATOIRE** |
| `TAILSCALE_TAILNET` | - | **OBLIGATOIRE** |
| `FLASK_ENV` | `production` | Mode Flask (production/development) |

### Volumes

```yaml
postgres_data:    # Données PostgreSQL persistantes
logs:             # Logs Flask
web-page/:        # Code application (dev mode)
```

## 🔧 Opérations Courantes

### Arrêter les conteneurs

```bash
docker-compose down

# Garder les données (important!)
# Les données PostgreSQL sont dans le volume 'postgres_data'
```

### Reconstruire les images

```bash
docker-compose build --no-cache
docker-compose up -d
```

### Accéder à la base de données

#### Via Docker

```bash
docker-compose exec postgres psql -U iam_user -d iam_db

# Une fois connecté:
\dt                      # Voir les tables
SELECT * FROM access_requests;
```

#### Via PgAdmin (UI)

1. Démarrer: `docker-compose --profile debug up -d`
2. Aller à http://localhost:5050
3. Login: admin@example.com / admin
4. Ajouter serveur:
   - Host: `postgres`
   - Port: `5432`
   - Database: `iam_db`
   - Username: `iam_user`
   - Password: (celle de `.env`)

### Voir les logs

```bash
# Logs Flask (en direct)
docker-compose logs -f web

# Logs PostgreSQL
docker-compose logs -f postgres

# Logs d'un conteneur spécifique
docker-compose logs -f [service]
```

### Exécuter des commandes dans le conteneur

```bash
# Linux/Shell
docker-compose exec web bash

# Python
docker-compose exec web python3 -c "from app import app, db; ..."

# Cron job (test)
docker-compose exec web python3 scripts/expire_access.py
```

## 📅 Configuration du Cron Job

### En Docker (Recommandé)

Créer une tâche cron sur l'hôte:

```bash
crontab -e
```

Ajouter:
```cron
# Expirer les accès toutes les 6 heures
0 */6 * * * docker exec iam_web python3 scripts/expire_access.py >> /var/log/iam_cron.log 2>&1
```

### Test manuel

```bash
docker-compose exec web python3 scripts/expire_access.py
```

## 🐛 Dépannage

### Erreur: "Cannot connect to PostgreSQL"

```bash
# Vérifier que PostgreSQL a démarré
docker-compose logs postgres | grep -i "ready"

# Vérifier la connexion
docker-compose exec web python3 -c "
import os
from sqlalchemy import create_engine
url = f'postgresql://iam_user:iam_password_change_me@postgres:5432/iam_db'
engine = create_engine(url)
print('✅ Connexion OK')
"
```

### Erreur: "Database does not exist"

```bash
# Recréer les tables
docker-compose exec web python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('✅ Tables créées')
"
```

### Erreur: "Tailscale API timeout"

1. Vérifier `TAILSCALE_API_TOKEN` dans `.env`
2. Vérifier la connectivité Internet
3. Test:
```bash
docker-compose exec web python3 -c "
from app import get_tailscale_devices
devices = get_tailscale_devices()
print(f'✅ {len(devices)} devices trouvés')
"
```

### Erreur: "Port 5000 already in use"

```bash
# Changer le port dans docker-compose.yml
# Ligne: ports: - "5001:5000"  # Utilise 5001

docker-compose down
docker-compose up -d
```

### PgAdmin ne démarre pas

```bash
# PgAdmin nécessite le profile 'debug'
docker-compose --profile debug up -d pgadmin

# Vérifier
docker-compose logs pgadmin
```

## 📊 Monitoring

### Healthcheck

```bash
# Docker affiche automatiquement la santé des conteneurs
docker-compose ps

# STATUS: Up (healthy) ✓
# STATUS: Up (unhealthy) ✗
```

### Statistiques

```bash
# Utilisation des ressources
docker stats -d

# Espace disque utilisé
docker system df
```

## 🔐 Sécurité (Production)

### Changez les mots de passe!

```env
# AVANT PRODUCTION:
DB_PASSWORD=super_long_random_secure_password_here
PGADMIN_PASSWORD=another_secure_password
```

### Utilisez HTTPS

```yaml
# Dans docker-compose.yml:
environment:
  FLASK_SSL_CERT=/etc/ssl/certs/cert.pem
  FLASK_SSL_KEY=/etc/ssl/private/key.pem
```

### Limitez l'accès réseau

```yaml
# docker-compose.yml
services:
  web:
    ports:
      - "127.0.0.1:5000:5000"  # Localhost seulement
```

### Nettoyez régulièrement

```bash
# Supprimer les images non utilisées
docker image prune

# Supprimer les volumes orphelins
docker volume prune

# Supprimer tout (ATTENTION!)
docker system prune
```

## 📚 Fichiers Importants

```
PFE/
├── docker-compose.yml          # Orchestration
├── Dockerfile                  # Build Flask
├── web-page/
│   ├── .env                    # Variables (créer depuis .env.example)
│   ├── .env.example            # Template
│   ├── requirements.txt        # Dépendances Python
│   ├── app.py                  # Application
│   └── scripts/
│       └── expire_access.py    # Cron job
└── DEPLOYMENT_GUIDE.md         # (Ancien - pour référence)
```

## ✅ Checklist Final

- [ ] Docker et Docker Compose installés
- [ ] `.env` créé avec vos valeurs
- [ ] `docker-compose up -d` réussi
- [ ] `docker-compose ps` montre les conteneurs "healthy"
- [ ] http://localhost:5000 accessible
- [ ] Login fonctionne
- [ ] Cron job configuré
- [ ] Logs visibles dans `docker-compose logs -f web`

## 📞 Support

```bash
# Vérifier la version de Docker
docker --version
docker-compose --version

# Logs complets incluant les erreurs
docker-compose logs --tail 100

# Rebuilt depuis zéro
docker-compose down -v  # ATTENTION: Supprime les données!
docker-compose build --no-cache
docker-compose up -d
```

---

**Status:** ✅ Prêt pour production avec Docker
**Date:** 2025-03-12
