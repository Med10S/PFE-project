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
sys.path.insert(0, os.path.dirname(__file__))

from models import AccessRequest, db
from ACL_work.tailscale_acl_api import (
    cleanup_expired_requests
)
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

        for access in expired_accesses:
            access.status = 'expired'
            print(f"[EXPIRATION] {access.user_name} - Accès à {access.server_name} expiré")
            removed_count, removed_list = cleanup_expired_requests(AccessRequest, db)

            print(f"Nettoyage effectué:")
            print(f"  - Accès supprimés: {removed_count}")
            if removed_list:
                print(f"  - Détails:")
                for access in removed_list:
                    print(f"    • {access}")
            else:
                print(f"  - Rien à nettoyer")

        session.commit()
        session.close()

        print(f"\n✅ Script d'expiration terminé: {count} accès expirés")
        return True

    except Exception as e:
        print(f"❌ Erreur lors de l'expiration des accès: {e}")
        return False

if __name__ == '__main__':
    success = expire_old_accesses()
    sys.exit(0 if success else 1)
