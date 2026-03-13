# Guide de Déploiement Complet

## ✅ Étapes Complétées

### 1️⃣ Extraction des Tags Utilisateur ✓
- Les groupes Authentik sont mappés aux tags Tailscale
- Automatique lors de chaque connexion utilisateur
- Fichier: `auth.py` - Classe `User.get_user_tags()`

### 2️⃣ Table PostgreSQL ✓
- Table `access_requests` créée automatiquement
- Stockage: User, Serveur, Status, Timestamps
- Fichier: `models.py` - Classe `AccessRequest`

### 3️⃣ Enregistrement des Demandes ✓
- Route API: `POST /api/request-access`
- Vérification des demandes en doublon
- Fichier: `app.py` - fonction `api_request_access()`

### 4️⃣ Dashboard Admin de Gestion ✓
- 3 onglets: Pending, Approved, Denied
- Actions: Approuver dengan notes, Rejeter avec raison
- Fichier: `templates/admin_access_requests.html`

### 5️⃣ Cron Job d'Expiration ✓
- Script Python exécutable
- Expire les accès après 3 jours
- Fichier: `scripts/expire_access.py`

### 6️⃣ Menu Conditionnel ✓
- Affiche "Demandes d'Accès" que pour les admins
- Basé sur le groupe Authentik
- Fichier: `templates/base.html`

---

## 🚀 Prochaines Étapes (CRÍTICAS)

### À FAIRE IMMÉDIATEMENT

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer les variables d'environnement
cp .env.example .env
# ÉDITER .env avec vos vraies valeurs!
```

### Variables d'Environnement Requises

```env
# TAILSCALE
TAILSCALE_API_TOKEN=<votre_token>      # https://tailscale.com/admin/settings
TAILSCALE_TAILNET=<votre_tailnet>      # ex: "company.com"

# POSTGRESQL
DATABASE_URL=postgresql://user:pass@localhost:5432/iam_db

# AUTHENTIK (ne pas changer les URLs, juste les IDs)
AUTHENTIK_CLIENT_ID=<votre_client_id>
AUTHENTIK_CLIENT_SECRET=<votre_client_secret>
```

### Test de la Connexion

```bash
# Tester Tailscale API
python3 -c "
from app import get_tailscale_devices
devices = get_tailscale_devices()
print(f'✅ {len(devices)} devices trouvés')
"

# Tester PostgreSQL
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('✅ Tables créées')
"
```

### Configurer le Cron Job

```bash
# Voir le fichier de setup
cat scripts/CRON_SETUP.txt

# Pour test local (tous les 10 minutes):
*/10 * * * * cd /path/to/web-page && python3 scripts/expire_access.py

# Pour production (toutes les 6 heures):
0 */6 * * * cd /path/to/web-page && python3 scripts/expire_access.py >> logs/cron.log 2>&1
```

### Variables de Mapping (Authentik → Tailscale)

Si vos groupes Authentik sont différents, modifier `auth.py`:

```python
group_to_tag_mapping = {
    'dev': 'tag:dev',           # ← Changer si besoin
    'prod': 'tag:prod',
    'admin': 'tag:admin',
    'read_users': 'tag:user',
    'Admins': 'tag:admin',
}
```

---

## 🔧 Configuration Avancée

### 1. Intégration Tailscale ACL (Optionnel)

```python
# Pour ajouter automatiquement l'utilisateur au groupe Tailscale:
# File: tailscale_acl_integration.py (À implémenter)

# Actuellement: Approving = status change only
# Future: Approving = status + ACL modification
```

### 2. Notifications Email (Optionnel)

```python
# À ajouter dans app.py
from flask_mail import Mail, Message

mail = Mail(app)

def send_approval_email(user_email, server_name):
    msg = Message(
        f"Votre demande d'accès à {server_name} est approuvée",
        recipients=[user_email]
    )
    mail.send(msg)
```

### 3. Audit Logging Complet (Optionnel)

```python
# Ajouter à models.py
class AuditLog(db.Model):
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(255))  # 'request', 'approve', 'deny'
    user = db.Column(db.String(255))
    details = db.Column(db.Text)
```

---

## 📊 Monitoring & Logs

```bash
# Créer les répertoires de logs
mkdir -p logs

# Voir les logs cron
tail -f logs/cron.log

# Voir les logs Flask
tail -f logs/flask.log
```

---

## 🧪 Test Complet du Flux

### Scénario de Test

1. **Créer un utilisateur test** dans Authentik
   - Groupe: "dev" (pas admin)

2. **Connexion** avec cet utilisateur
   - Doit voir le dashboard user
   - Pas d'accès à "Demandes d'Accès"

3. **Demander l'accès** à un serveur
   - Button "Demander Accès" apparaît
   - Demande enregistrée en DB

4. **Admin approuve** la demande
   - Aller sur `/admin/access-requests`
   - Cliquer "Approuver"
   - Status change à "approved"
   - expires_at = now + 3 jours

5. **Cron job expire** l'accès
   - Attendre 3 jours OU modifier la date en DB
   - `UPDATE access_requests SET expires_at = now WHERE id = 1`
   - Lancer: `python3 scripts/expire_access.py`
   - Status doit passer à "expired"

---

## 🐛 Debugging

### Mode Debug Flask

```bash
export FLASK_DEBUG=1
export FLASK_ENV=development
python3 app.py
```

### Vérifier les Groupes/Tags Utilisateur

```bash
python3 -c "
from flask import session
from auth import get_current_user

# Dans une route:
user = get_current_user()
print(f'Groups: {user.groups}')
print(f'Tags: {user.tags}')
"
```

### Vérifier la Base de Données

```bash
psql postgresql://user:pass@localhost:5432/iam_db

# Voir les demandes
\d access_requests
SELECT * FROM access_requests;

# Voir les demandes pending
SELECT * FROM access_requests WHERE status = 'pending';
```

---

## 📝 Checklist Final

- [ ] Dépendances installées: `pip install -r requirements.txt`
- [ ] .env créé et configuré avec les vraies valeurs
- [ ] PostgreSQL créé et connecté
- [ ] Tables créées: `python3 -c "from app import app, db; app.app_context().push(); db.create_all()"`
- [ ] Cron job configuré: `crontab -e`
- [ ] Test Tailscale API: Devices récupérés
- [ ] Test Authentik OAuth: Login fonctionne
- [ ] Test flux demandes: Request → Approve → Check DB
- [ ] Email ready (optionnel)

---

## 📞 Support

Pour toute question ou problème:
1. Vérifier les logs: `logs/flask.log`, `logs/cron.log`
2. Consulter README.md
3. Vérifier les variables .env
4. Tester les APIs directement

---

**Fait par:** Claude
**Date:** 2025-03-12
**Status:** ✅ Prêt pour déploiement
