# Script de configuration Authentik pour l'application Flask IAM (Windows)
Write-Host "🔐 Configuration Authentik IAM Dashboard" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Variables
$AUTHENTIK_URL = "http://localhost:9090"
$APP_CLIENT_ID = "flask-iam-dashboard"
$APP_REDIRECT_URI = "http://localhost:5000/auth/callback"

Write-Host ""
Write-Host "📋 Étapes de configuration :" -ForegroundColor Yellow
Write-Host "1. Générer les mots de passe sécurisés"
Write-Host "2. Démarrer Authentik"
Write-Host "3. Configurer l'application OAuth2"
Write-Host "4. Créer les groupes et permissions"
Write-Host ""

# Génération des mots de passe
Write-Host "🔑 Génération des secrets..." -ForegroundColor Green
$PG_PASS = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString()))
$AUTHENTIK_SECRET = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString() + [System.Guid]::NewGuid().ToString()))

# Création du fichier .env avec les vraies valeurs
$envContent = @"
# Configuration PostgreSQL
PG_PASS=$PG_PASS
PG_USER=authentik  
PG_DB=authentik

# Configuration Authentik
AUTHENTIK_SECRET_KEY=$AUTHENTIK_SECRET
AUTHENTIK_ERROR_REPORTING__ENABLED=false
AUTHENTIK_LOG_LEVEL=info

# Configuration des ports
COMPOSE_PORT_HTTP=9090
COMPOSE_PORT_HTTPS=9443
"@

$envContent | Out-File -FilePath "authentik.env" -Encoding UTF8

Write-Host "✅ Fichier authentik.env généré avec des secrets sécurisés" -ForegroundColor Green

# Démarrage d'Authentik
Write-Host ""
Write-Host "🚀 Démarrage d'Authentik..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "⏳ Attente du démarrage complet d'Authentik (30 secondes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "🌐 Configuration manuelle requise :" -ForegroundColor Cyan
Write-Host "1. Ouvrir $AUTHENTIK_URL dans votre navigateur"
Write-Host "2. Compléter l'installation initiale (créer le compte admin)"
Write-Host "3. Aller dans Admin Interface > Applications > Providers"
Write-Host "4. Créer un nouveau Provider OAuth2/OpenID Connect :"
Write-Host "   - Nom: Flask IAM Dashboard"
Write-Host "   - Client type: Confidential"
Write-Host "   - Client ID: $APP_CLIENT_ID"
Write-Host "   - Redirect URI: $APP_REDIRECT_URI"
Write-Host "   - Scopes: openid, profile, email, groups, offline_access"
Write-Host ""
Write-Host "5. Créer les groupes :" -ForegroundColor Yellow
Write-Host "   - Groupe 'Admins' (permissions: users:read, users:update, servers:manage)"
Write-Host "   - Groupe 'read_users' (permission: users:read)"
Write-Host ""
Write-Host "6. Créer des utilisateurs de test et les assigner aux groupes"
Write-Host ""
Write-Host "7. Mettre à jour auth.py avec le vrai Client ID et Client Secret"
Write-Host ""

Write-Host "📝 Configuration du client OAuth2 :" -ForegroundColor Magenta
Write-Host "   Client ID: $APP_CLIENT_ID"
Write-Host "   Authorization URL: $AUTHENTIK_URL/application/o/authorize/"
Write-Host "   Token URL: $AUTHENTIK_URL/application/o/token/"
Write-Host "   UserInfo URL: $AUTHENTIK_URL/application/o/userinfo/"
Write-Host "   Redirect URI: $APP_REDIRECT_URI"
Write-Host ""

Write-Host ""
