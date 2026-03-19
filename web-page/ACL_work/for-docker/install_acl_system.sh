#!/bin/bash
# Installation et déploiement du système ACL Tailscale

# Configuration
PROJECT_DIR="/home/mohammedsbihi/PFE/web-page"
LOG_DIR="/var/log/tailscale-acl"
BACKUP_DIR="/var/backups/acl"

echo "=== Installation du système ACL Tailscale ==="

# 1. Créer les répertoires nécessaires
echo "1. Création des répertoires..."
sudo mkdir -p "$LOG_DIR"
sudo mkdir -p "$BACKUP_DIR"
sudo chmod 755 "$LOG_DIR"
sudo chmod 755 "$BACKUP_DIR"

# 2. Copier le fichier ACL s'il n'existe pas
echo "2. Configuration du fichier ACL..."
if [ ! -f "$PROJECT_DIR/acl.json" ]; then
    cp "$PROJECT_DIR/ACL.exemple.json" "$PROJECT_DIR/acl.json"
    echo "   ✓ Fichier ACL créé"
else
    echo "   ✓ Fichier ACL existe déjà"
fi

# 3. Installer les dépendances Python
echo "3. Installation des dépendances..."
cd "$PROJECT_DIR"
pip install pytest pytest-cov  # Pour les tests

# 4. Exécuter les tests
echo "4. Exécution des tests..."
python -m pytest "$PROJECT_DIR/test_tailscale_acl.py" -v

if [ $? -ne 0 ]; then
    echo "   ✗ Les tests ont échoué!"
    exit 1
fi
echo "   ✓ Tests réussis"

# 5. Configurer le cron job
echo "5. Configuration du cron job..."
CRON_JOB="*/30 * * * * cd \"$PROJECT_DIR\" && /usr/bin/python3 cleanup_expired_access.py >> \"$LOG_DIR/cleanup.log\" 2>&1"

# Vérifier si le cron job existe déjà
if crontab -l 2>/dev/null | grep -q "cleanup_expired_access.py"; then
    echo "   ✓ Cron job déjà configuré"
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "   ✓ Cron job configuré"
fi

# 6. Créer le fichier .env
echo "6. Configuration des variables d'environnement..."
cat > "$PROJECT_DIR/.env.acl" <<EOF
# Fichier ACL utilisé en développement
TAILSCALE_ACL_FILE=$PROJECT_DIR/acl.json

# Fichier ACL actuel de Tailscale (à adapter selon votre installation)
TAILSCALE_ACL_CURRENT=/etc/tailscale/acl.json

# Token API Tailscale (à remplir)
TAILSCALE_API_TOKEN=

# ID Tailnet (à remplir)
TAILSCALE_TAILNET=

# Logs
LOG_DIR=$LOG_DIR
BACKUP_DIR=$BACKUP_DIR
EOF

echo "   ✓ Fichier .env.acl créé (à remplir avec vos valeurs)"

# 7. Afficher les permissions
echo "7. Vérification des permissions..."
chmod +x "$PROJECT_DIR/cleanup_expired_access.py"
chmod +x "$PROJECT_DIR/grant_access.py"
chmod +x "$PROJECT_DIR/revoke_access.py"
echo "   ✓ Permissions configurées"

# 8. Afficher un résumé
echo ""
echo "=== Installation terminée ==="
echo ""
echo "Prochaines étapes:"
echo "1. Éditer $PROJECT_DIR/.env.acl avec vos valeurs:"
echo "   - TAILSCALE_API_TOKEN"
echo "   - TAILSCALE_TAILNET"
echo ""
echo "2. Tester manuellement:"
echo "   python grant_access.py test@sbihi.tech tag:machine-1 24"
echo "   python revoke_access.py test@sbihi.tech tag:machine-1"
echo ""
echo "3. Vérifier les logs du cron job:"
echo "   tail -f $LOG_DIR/cleanup.log"
echo ""
echo "4. Intégrer les endpoints Flask (voir ACL_INTEGRATION_EXAMPLE.py)"
echo ""
