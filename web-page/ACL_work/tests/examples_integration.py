#!/usr/bin/env python3
"""
Exemple pratique: comment utiliser le nouveau système ACL + BD

Ce script montre les 3 cas d'usage principaux:
1. Approuver une demande d'accès (grant ACL + update BD)
2. Révoquer un accès avant expiration (revoke ACL + update BD)
3. Nettoyer tous les accès expirés (cron/scheduler)
"""

import os
import sys
from datetime import datetime, timedelta

# Ajoute automatiquement le dossier web-page au PYTHONPATH.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_PAGE_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))
if WEB_PAGE_ROOT not in sys.path:
    sys.path.insert(0, WEB_PAGE_ROOT)

from models import AccessRequest, db
from ACL_work.tailscale_acl_api import (
    approve_access_request,
    revoke_access_request,
    cleanup_expired_requests
)


def example_1_approve_access():
    """
    Cas 1: Un admin approuve une demande d'accès
    - La règle ACL est ajoutée à Tailscale
    - La demande est marquée comme "approved" en BD
    """
    print("\n=== EXEMPLE 1: Approuver une demande d'accès ===\n")

    # Récupérer une demande en attente
    pending_req = AccessRequest.query.filter_by(status='pending').first()

    if not pending_req:
        print("Aucune demande en attente trouvée")
        return

    print(f"Demande trouvée: {pending_req.user_email} -> {pending_req.server_name}")

    # Approuver la demande ces infos doivent etre fournies par API ou interface admin via la db
    admin_email = "admin@example.com"
    tailscale_tag = "tag:machine-1"

    success, msg = approve_access_request(pending_req, admin_email, tailscale_tag)

    if success:
        db.session.commit()  # Important!
        print(f"✓ Succès: {msg}")
        print(f"  - Statut BD: {pending_req.status}")
        print(f"  - ACL appliquée: {pending_req.acl_applied}")
        print(f"  - Expire à: {pending_req.expires_at}")
    else:
        db.session.rollback()
        print(f"✗ Erreur: {msg}")


def example_2_revoke_access():
    """
    Cas 2: Un admin révoque un accès avant expiration
    - La règle ACL est supprimée de Tailscale
    - La demande est marquée comme "revoked" ou "expired" en BD
    """
    print("\n=== EXEMPLE 2: Révoquer un accès ===\n")

    # Récupérer une demande approuvée
    approved_req = AccessRequest.query.filter_by(status='approved', acl_applied=True).first()

    if not approved_req:
        print("Aucune demande approuvée trouvée")
        return

    print(f"Demande trouvée: {approved_req.user_email} -> {approved_req.server_name}")
    print(f"Tag Tailscale: {approved_req.tailscale_tag}")

    # Révoquer l'accès
    success, msg = revoke_access_request(approved_req)

    if success:
        db.session.commit()  # Important!
        print(f"✓ Succès: {msg}")
        print(f"  - Statut BD: {approved_req.status}")
        print(f"  - ACL appliquée: {approved_req.acl_applied}")
    else:
        db.session.rollback()
        print(f"✗ Erreur: {msg}")


def example_3_cleanup_expired():
    """
    Cas 3: Nettoyer tous les accès expirés
    - Automatiquement appelé par cron ou scheduler
    - Pour chaque demande expirée:
      - Supprime la règle ACL de Tailscale
      - Met à jour le statut en BD
    """
    print("\n=== EXEMPLE 3: Nettoyer les accès expirés ===\n")

    removed_count, removed_list = cleanup_expired_requests(AccessRequest, db)

    print(f"Nettoyage effectué:")
    print(f"  - Accès supprimés: {removed_count}")
    if removed_list:
        print(f"  - Détails:")
        for access in removed_list:
            print(f"    • {access}")
    else:
        print(f"  - Rien à nettoyer")


def example_4_check_status():
    """
    Cas 4: Vérifier l'état des demandes en BD
    """
    print("\n=== EXEMPLE 4: État des demandes ===\n")

    pending  = AccessRequest.query.filter_by(status='pending').count()
    approved = AccessRequest.query.filter_by(status='approved').count()
    expired  = AccessRequest.query.filter_by(status='expired').count()
    denied   = AccessRequest.query.filter_by(status='denied').count()

    print(f"Résumé des demandes:")
    print(f"  - En attente: {pending}")
    print(f"  - Approuvées: {approved}")
    print(f"  - Expirées: {expired}")
    print(f"  - Rejetées: {denied}")

    # Afficher les demandes approuvées qui arrivent bientôt à expiration
    now = datetime.utcnow()
    soon = now + timedelta(hours=1)

    expiring_soon = AccessRequest.query.filter(
        AccessRequest.status == 'approved',
        AccessRequest.expires_at <= soon,
        AccessRequest.expires_at > now
    ).all()

    if expiring_soon:
        print(f"\nDemandes expirant dans l'heure:")
        for req in expiring_soon:
            remaining = req.expires_at - now
            minutes = remaining.total_seconds() / 60
            print(f"  • {req.user_email} -> {req.server_name}")
            print(f"    Expire dans {int(minutes)} min")


if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    DATABASE_URL = f'postgresql://iam_user:change_me_to_secure_password@172.210.137.97:5432/iam_db'

    # À adapter avec votre configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

    db.init_app(app)

    with app.app_context():
        # Initialise le schéma local pour éviter les erreurs 'no such table'.
        db.create_all()

        # Exemples
        example_4_check_status()
        example_1_approve_access()
        example_2_revoke_access()
        # example_3_cleanup_expired()
