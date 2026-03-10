#!/bin/bash

# Script de configuration Authentik pour l'application Flask IAM
echo "🔐 Configuration Authentik IAM Dashboard"
echo "======================================="

# Variables
AUTHENTIK_URL="http://localhost:9090"
APP_CLIENT_ID="flask-iam-dashboard"
APP_REDIRECT_URI="http://localhost:5000/auth/callback"

echo ""
echo "📋 Étapes de configuration :"
echo "1. Générer les mots de passe sécurisés"
echo "2. Démarrer Authentik"
echo "3. Configurer l'application OAuth2"
echo "4. Créer les groupes et permissions"
echo ""

# Génération des mots de passe
echo "🔑 Génération des secrets..."
PG_PASS=$(openssl rand -base64 36 | tr -d '\n')
AUTHENTIK_SECRET=$(openssl rand -base64 60 | tr -d '\n')

# Création du fichier .env avec les vraies valeurs
cat > authentik.env << EOF
# Configuration PostgreSQL
PG_PASS=${PG_PASS}
PG_USER=authentik
PG_DB=authentik

# Configuration Authentik
AUTHENTIK_SECRET_KEY=${AUTHENTIK_SECRET}
AUTHENTIK_ERROR_REPORTING__ENABLED=false
AUTHENTIK_LOG_LEVEL=info

# Configuration des ports
COMPOSE_PORT_HTTP=9090
COMPOSE_PORT_HTTPS=9443
EOF

echo "✅ Fichier authentik.env généré avec des secrets sécurisés"

# Démarrage d'Authentik
echo ""
echo "🚀 Démarrage d'Authentik..."
docker-compose up -d

echo "⏳ Attente du démarrage complet d'Authentik (30 secondes)..."
sleep 30

echo ""
echo "🌐 Configuration manuelle requise :"
echo "1. Ouvrir ${AUTHENTIK_URL} dans votre navigateur"
echo "2. Compléter l'installation initiale (créer le compte admin)"
echo "3. Aller dans Admin Interface > Applications > Providers"
echo "4. Créer un nouveau Provider OAuth2/OpenID Connect :"
echo "   - Nom: Flask IAM Dashboard"
echo "   - Client type: Confidential"
echo "   - Client ID: ${APP_CLIENT_ID}"
echo "   - Redirect URI: ${APP_REDIRECT_URI}"
echo "   - Scopes: openid, profile, email, groups, offline_access"
echo ""
echo "5. Créer les groupes :"
echo "   - Groupe 'Admins' (permissions: users:read, users:update, servers:manage)"
echo "   - Groupe 'read_users' (permission: users:read)"
echo ""
echo "6. Créer des utilisateurs de test et les assigner aux groupes"
echo ""
echo "7. Mettre à jour auth.py avec le vrai Client ID et Client Secret"
echo ""

echo "📝 Configuration du client OAuth2 :"
echo "   Client ID: ${APP_CLIENT_ID}"
echo "   Authorization URL: ${AUTHENTIK_URL}/application/o/authorize/"
echo "   Token URL: ${AUTHENTIK_URL}/application/o/token/"
echo "   UserInfo URL: ${AUTHENTIK_URL}/application/o/userinfo/"
echo "   Redirect URI: ${APP_REDIRECT_URI}"
echo ""

echo "🎯 Une fois la configuration terminée, démarrer l'app Flask :"
echo "   python app.py"
echo ""
echo "✅ Configuration initiale terminée!"