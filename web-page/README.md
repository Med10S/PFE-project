# Application Web IAM avec Authentik et Dashboard

Cette application Flask fournit un système d'authentification IAM (Identity and Access Management) intégré avec **Authentik** comme provider OAuth2/OIDC, avec des tableaux de bord différenciés selon les rôles et permissions des utilisateurs.

## 🚀 Fonctionnalités

### 🔐 Authentification Authentik IAM
- Intégration OAuth2/OIDC avec Authentik
- Authentification sécurisée avec PKCE
- Gestion des sessions avec refresh tokens
- Single Sign-On (SSO) ready

### 👥 Gestion des Rôles et Permissions
- **Groupe Admins** (`Admins`) avec permissions :
  - `users:read` - Lecture des utilisateurs
  - `users:update` - Modification des utilisateurs  
  - `servers:manage` - Gestion des serveurs
  
- **Groupe Utilisateurs** (`read_users`) avec permission :
  - `users:read` - Lecture seule des utilisateurs

### 📊 Tableaux de Bord
- **Dashboard Administrateur** : Gestion complète des utilisateurs et serveurs
- **Dashboard Utilisateur** : Consultation en lecture seule
- **Profil Utilisateur** : Informations personnelles et gestion de session

## 🛠️ Installation Rapide

### Prérequis
- Docker et Docker Compose
- Python 3.8+
- pip

### 1. Configuration Automatique

**Windows :**
```powershell
# Exécuter le script de configuration
.\setup_authentik.ps1
```

**Linux/macOS :**
```bash
# Rendre le script exécutable et l'exécuter
chmod +x setup_authentik.sh
./setup_authentik.sh
```

### 2. Installation Manuelle

1. **Cloner et installer les dépendances**
   ```bash
   # Installation des dépendances Python
   pip install -r requirements.txt
   ```

2. **Configurer Authentik**
   ```bash
   # Générer les secrets (Linux/macOS)
   echo "PG_PASS=$(openssl rand -base64 36 | tr -d '\n')" > authentik.env
   echo "AUTHENTIK_SECRET_KEY=$(openssl rand -base64 60 | tr -d '\n')" >> authentik.env
   
   # Démarrer Authentik
   docker-compose up -d
   ```

3. **Configuration initiale Authentik**
   - Ouvrir http://localhost:9090
   - Compléter l'installation initiale (créer le compte `akadmin`)

## ⚙️ Configuration Détaillée

### Configuration OAuth2 dans Authentik

1. **Accéder à l'interface Admin Authentik** : http://localhost:9090
2. **Créer un Provider OAuth2** :
   - Aller à `Applications > Providers > Create`
   - Type : `OAuth2/OpenID Provider`
   - Name : `Flask IAM Dashboard`
   - Client type : `Confidential`
   - Client ID : `flask-iam-dashboard`
   - Redirect URIs : `http://localhost:5000/auth/callback`
   - Scopes : `openid profile email groups offline_access`

3. **Créer l'Application** :
   - Aller à `Applications > Applications > Create`
   - Name : `Flask IAM Dashboard`
   - Slug : `flask-iam-dashboard`
   - Provider : Sélectionner le provider créé précédemment

4. **Récupérer les credentials** :
   - Noter le `Client ID` et `Client Secret`
   - Mettre à jour `auth.py` avec ces valeurs

### Configuration des Groupes et Permissions

1. **Créer les Groupes** :
   ```
   Directory > Groups > Create:
   - Nom: "Admins"
   - Nom: "read_users"
   ```

2. **Créer des Utilisateurs de Test** :
   ```
   Directory > Users > Create:
   - admin@example.com (groupe: Admins)
   - user@example.com (groupe: read_users)
   ```

3. **Assigner les Utilisateurs aux Groupes** :
   - Éditer chaque utilisateur
   - Ajouter aux groupes appropriés

### Mise à jour de la Configuration App

Modifier `auth.py` ligne 15-17 :
```python
OAUTH_CONFIG = {
    'client_id': 'votre_client_id_reel',
    'client_secret': 'votre_client_secret_reel',
    # ... reste de la config
}
```

## 🚀 Lancement de l'Application

```bash
# Démarrer l'application Flask
python app.py
```

Accéder à l'application : http://localhost:5000

## 📁 Structure du Projet

```
web-page/
├── app.py                     # Application Flask principale  
├── auth.py                    # Système d'authentification Authentik OAuth2
├── requirements.txt           # Dépendances Python
├── docker-compose.yml         # Configuration Authentik
├── authentik.env             # Variables d'environnement Authentik
├── setup_authentik.sh        # Script de configuration (Linux/macOS)
├── setup_authentik.ps1       # Script de configuration (Windows)
├── templates/           
│   ├── base.html             # Template de base
│   ├── login_authentik.html  # Page de connexion Authentik
│   ├── admin_dashboard.html  # Dashboard administrateur
│   ├── user_dashboard.html   # Dashboard utilisateur
│   └── profile.html          # Profil utilisateur
└── static/
    └── style.css             # Styles CSS personnalisés
```

## 🔗 API Endpoints

### Authentification
- `GET /login` - Page de connexion (redirige vers Authentik)
- `GET /auth/callback` - Callback OAuth2 Authentik
- `GET /logout` - Déconnexion
- `GET /profile` - Profil utilisateur

### Dashboards  
- `GET /` - Redirection vers le dashboard approprié
- `GET /admin/dashboard` - Dashboard administrateur (rôle: Admins)
- `GET /user/dashboard` - Dashboard utilisateur (rôle: read_users)

### API REST
- `GET /api/users` - Liste des utilisateurs (permission: users:read)
- `PUT /api/users/<id>` - Modifier un utilisateur (permission: users:update)
- `GET /api/servers` - Liste des serveurs (permission: servers:manage)
- `POST /api/servers/<id>/restart` - Redémarrer un serveur (permission: servers:manage)
- `POST /api/refresh-token` - Rafraîchir le token d'accès

## 🔐 Sécurité et Permissions

### Par Rôle

#### Administrateurs (Admins)
✅ Consulter tous les utilisateurs  
✅ Modifier les utilisateurs  
✅ Gérer les serveurs  
✅ Redémarrer les serveurs  
✅ Accès complet au dashboard  
✅ Profil utilisateur complet

#### Utilisateurs (read_users)  
✅ Consulter la liste des utilisateurs  
✅ Voir les détails utilisateur  
✅ Statistiques générales  
✅ Profil utilisateur en lecture seule  
❌ Modification des données  
❌ Gestion des serveurs

### Fonctionnalités de Sécurité
- Authentification OAuth2/OIDC avec PKCE
- Tokens JWT sécurisés  
- Refresh tokens pour sessions longues
- Vérification des permissions pour chaque action
- Protection CSRF avec state parameter
- Sessions Flask sécurisées

## 🐳 Docker et Authentik

### Services Authentik
- **PostgreSQL** : Base de données Authentik
- **Redis** : Cache et sessions
- **Authentik Server** : Interface web et API
- **Authentik Worker** : Tâches en arrière-plan

### Ports par Défaut
- **Authentik** : http://localhost:9090, https://localhost:9443
- **Flask App** : http://localhost:5000

### Commandes Docker Utiles
```bash
# Voir les logs Authentik
docker-compose logs -f server

# Redémarrer Authentik
docker-compose restart

# Arrêter Authentik  
docker-compose down

# Supprimer complètement (attention: perte de données!)
docker-compose down -v
```

## 🔧 Développement

### Ajouter de Nouveaux Utilisateurs
Les utilisateurs sont gérés dans Authentik. Créer via l'interface web ou l'API Authentik.

### Ajouter de Nouvelles Permissions
1. Définir la permission dans le modèle utilisateur (auth.py)
2. Créer les décorateurs appropriés  
3. Implémenter la logique métier
4. Configurer les groupes dans Authentik avec les claims appropriés

### Personnaliser l'Interface
- Modifier les templates dans `templates/`
- Adapter les styles dans `static/style.css`
- Ajouter des routes dans `app.py`

## 🆘 Dépannage

### Problèmes Communs

**1. Authentik non accessible**
```bash
# Vérifier que les services sont démarrés
docker-compose ps

# Vérifier les logs
docker-compose logs server
```

**2. Erreur OAuth2 "Invalid redirect URI"**
- Vérifier que l'URI de redirection dans Authentik correspond exactement
- URL: `http://localhost:5000/auth/callback`

**3. Permissions non synchronisées**  
- Vérifier que l'utilisateur est bien dans le bon groupe Authentik
- Vérifier que le scope `groups` est inclus dans la requête OAuth

**4. Token expiré**
- Utiliser le bouton "Rafraîchir Token" dans le profil
- Ou se reconnecter

### Logs de Debug
```bash
# Logs Flask (dans le terminal où vous avez lancé python app.py)
# Les erreurs OAuth apparaissent ici

# Logs Authentik
docker-compose logs -f server worker
```

## 🏢 Production

⚠️ **Important** : Cette configuration est pour le développement. Pour la production :

### Sécurité
1. **Changer toutes les clés secrètes** dans `authentik.env` et `app.py`  
2. **Utiliser HTTPS** pour Authentik et l'application Flask
3. **Configurer un vrai serveur PostgreSQL** (pas le container Docker)
4. **Utiliser un reverse proxy** (nginx, Traefik) 
5. **Configurer des certificats SSL/TLS** valides
6. **Utiliser un serveur WSGI** (Gunicorn, uWSGI) pour Flask
7. **Mettre en place une surveillance** et des backups

### Configuration Production Authentik
```bash
# Variables d'environnement production
AUTHENTIK_SECRET_KEY=<secret-vraiment-sur-64-caracteres>
AUTHENTIK_ERROR_REPORTING__ENABLED=true
AUTHENTIK_EMAIL__HOST=smtp.votre-domaine.com
AUTHENTIK_EMAIL__PORT=587
AUTHENTIK_EMAIL__USERNAME=authentik@votre-domaine.com
AUTHENTIK_EMAIL__PASSWORD=<mot-de-passe-email>
AUTHENTIK_EMAIL__USE_TLS=true
```

## 📄 Licence

Projet éducatif - Libre d'utilisation et de modification.

## 🤝 Support

Pour des questions sur Authentik : https://docs.goauthentik.io/  
Pour ce projet : Voir les issues GitHub ou créer une nouvelle issue.