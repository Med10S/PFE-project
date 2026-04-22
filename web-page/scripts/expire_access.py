#!/usr/bin/env python3
"""
Script de maintenance pour expirer les accès Tailscale après 3 jours
À exécuter via cron job: 0 */6 * * * docker exec iam_web python3 scripts/expire_access.py
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ajouter le répertoire parent au path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

from models import AccessRequest
from ACL_work.tailscale_acl_api import (
    revoke_access_request,
)
from audit import emit_audit_event
# Configuration de la base de données depuis les variables Docker
db_user = os.getenv('DB_USER', 'iam_user')
db_password = os.getenv('DB_PASSWORD', 'iam_password_change_me')
db_host = os.getenv('DB_HOST', 'postgres')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'iam_db')

DATABASE_URL = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'


def expire_old_accesses():
    """Expire les accès qui ont dépassé 3 jours"""
    try:
        # Créer la connexion
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Récupérer tous les accès approuvés qui ont expiré
        expired_accesses = session.query(AccessRequest).filter(
            AccessRequest.status == 'approved',
            AccessRequest.expires_at <= datetime.utcnow()
        ).all()

        count = len(expired_accesses)
        revoked_count = 0

        for access in expired_accesses:
            success, msg = revoke_access_request(access)
            if success:
                revoked_count += 1
                access.status = 'expired'
                emit_audit_event(
                    event='auto_revocation',
                    status='success',
                    user_email=access.user_email,
                    user_name=access.user_name,
                    server_id=access.server_id,
                    server_name=access.server_name,
                    request_id=access.id,
                    reason='ttl_expired',
                    ttl=access.expires_at.isoformat() if access.expires_at else '-',
                    message=msg,
                )
                print(f"[EXPIRATION] {access.user_name} - Accès à {access.server_name} révoqué")
            else:
                emit_audit_event(
                    event='auto_revocation',
                    status='failed',
                    user_email=access.user_email,
                    user_name=access.user_name,
                    server_id=access.server_id,
                    server_name=access.server_name,
                    request_id=access.id,
                    reason='ttl_expired',
                    ttl=access.expires_at.isoformat() if access.expires_at else '-',
                    message=msg,
                )
                print(f"[EXPIRATION] Échec de révocation pour {access.user_name} sur {access.server_name}: {msg}")

        session.commit()
        session.close()

        print(f"\n✅ Script d'expiration terminé: {count} expirés détectés, {revoked_count} révoqués")
        return True

    except Exception as e:
        print(f"❌ Erreur lors de l'expiration des accès: {e}")
        return False

if __name__ == '__main__':
    success = expire_old_accesses()
    sys.exit(0 if success else 1)
