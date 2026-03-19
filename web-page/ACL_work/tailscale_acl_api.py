"""
Endpoints API Flask pour la gestion des accès Tailscale via ACL
Intégration complète avec le système de demandes d'accès (models.AccessRequest)
"""

from flask import jsonify, request
from functools import wraps
import os
from datetime import datetime, timedelta
try:
    from .tailscale_acl_manager import TailscaleACLManager
except ImportError:
    # Fallback quand le fichier est exécuté directement depuis ACL_work.
    from tailscale_acl_manager import TailscaleACLManager

# Configuration depuis variables d'environnement
TAILSCALE_API_TOKEN = os.environ.get('TAILSCALE_API_TOKEN','')
TAILSCALE_TAILNET = os.environ.get('TAILSCALE_TAILNET','-')

# Instance globale du gestionnaire
acl_manager = None


def get_acl_manager():
    """Retourne l'instance du gestionnaire ACL (singleton pattern)"""
    global acl_manager
    if acl_manager is None:
        if not TAILSCALE_API_TOKEN or not TAILSCALE_TAILNET:
            print("Erreur: TAILSCALE_API_TOKEN et TAILSCALE_TAILNET doivent être définis")
            return None

        try:
            try:
                # Signature attendue localement: (api_token, tailnet)
                acl_manager = TailscaleACLManager(
                    api_token=TAILSCALE_API_TOKEN,
                    tailnet=TAILSCALE_TAILNET
                )
            except TypeError:
                # Fallback pour versions alternatives: (api_token)
                acl_manager = TailscaleACLManager(TAILSCALE_API_TOKEN)
        except Exception as e:
            print(f"Erreur lors de l'initialisation du manager ACL: {e}")
            acl_manager = False

    return acl_manager if acl_manager else None


def approve_access_request(access_request, admin_email, tailscale_tag):
    """
    Approuve une demande d'accès: mise à jour BD + application ACL

    Args:
        access_request: Instance du modèle AccessRequest
        admin_email: Email de l'admin qui approuve
        tailscale_tag: Tag Tailscale (ex: "tag:machine-1")

    Returns:
        tuple: (succès, message)
    """
    manager = get_acl_manager()
    if not manager:
        return False, "ACL manager non disponible"

    try:
        # 1. Appliquer la règle ACL à Tailscale
        success, acl_msg = manager.grant_access(access_request.user_email, tailscale_tag)

        if not success:
            return False, f"Erreur ACL: {acl_msg}"

        # 2. Mettre à jour la demande en BD
        access_request.status = 'approved'
        access_request.approved_at = datetime.utcnow()
        access_request.approved_by = admin_email
        access_request.expires_at = datetime.utcnow() + timedelta(days=3)
        access_request.tailscale_tag = tailscale_tag
        access_request.acl_applied = True
        access_request.admin_notes = f"ACL appliquée: {acl_msg}"

        # Commits via SQLAlchemy (suppose que db.session.commit() est appelé après)
        return True, acl_msg

    except Exception as e:
        return False, f"Erreur: {str(e)}"


def revoke_access_request(access_request):
    """
    Révoque un accès: suppression ACL + mise à jour BD

    Args:
        access_request: Instance du modèle AccessRequest

    Returns:
        tuple: (succès, message)
    """
    if not access_request.tailscale_tag or not access_request.acl_applied:
        return False, "Pas d'accès ACL à révoquer"

    manager = get_acl_manager()
    if not manager:
        return False, "ACL manager non disponible"

    try:
        # 1. Supprimer la règle ACL de Tailscale
        success, acl_msg = manager.revoke_access(
            access_request.user_email,
            access_request.tailscale_tag
        )

        if not success:
            return False, f"Erreur ACL: {acl_msg}"

        # 2. Mettre à jour la demande en BD
        access_request.status = 'expired'
        access_request.acl_applied = False

        return True, acl_msg

    except Exception as e:
        return False, f"Erreur: {str(e)}"


def cleanup_expired_requests(AccessRequest, db):
    """
    Nettoie tous les accès expirés: révoque ACL + marque statut comme expiré

    Args:
        AccessRequest: Modèle SQLAlchemy
        db: Instance SQLAlchemy

    Returns:
        tuple: (nombre supprimés, liste des accès supprimés)
    """
    from datetime import datetime

    now = datetime.utcnow()
    expired_reqs = AccessRequest.query.filter(
        AccessRequest.status == 'approved',
        AccessRequest.expires_at <= now,
        AccessRequest.acl_applied == True
    ).all()

    removed = []

    for req in expired_reqs:
        success, msg = revoke_access_request(req)
        if success:
            removed.append(f"{req.user_email} -> {req.server_name}")
            req.status = 'expired'
            db.session.add(req)

    if removed:
        db.session.commit()

    return len(removed), removed


# ===== Exemple d'intégration dans app.py avec le workflow =====
"""
À ajouter dans app.py pour intégrer l'ACL:

from models import AccessRequest, db
from ACL_work.tailscale_acl_api import approve_access_request, revoke_access_request, cleanup_expired_requests

# Route pour approuver une demande d'accès
@app.route('/api/access-request/<int:request_id>/approve', methods=['POST'])
@require_login
@in_groupe('authentik Admins')
def approve_request(request_id):
    access_req = AccessRequest.query.get(request_id)
    if not access_req:
        return jsonify({"error": "Demande non trouvée"}), 404

    # Récupérer le tag Tailscale (ex depuis une table de servers ou en param)
    tailscale_tag = request.get_json().get('tailscale_tag')  # ex: "tag:machine-1"

    success, msg = approve_access_request(
        access_req,
        get_current_user().email,
        tailscale_tag
    )

    if success:
        db.session.commit()
        return jsonify({"message": msg, "status": "approved"}), 200
    else:
        db.session.rollback()
        return jsonify({"error": msg}), 500

# Route pour révoquer un accès
@app.route('/api/access-request/<int:request_id>/revoke', methods=['POST'])
@require_login
@in_groupe('authentik Admins')
def revoke_request(request_id):
    access_req = AccessRequest.query.get(request_id)
    if not access_req:
        return jsonify({"error": "Demande non trouvée"}), 404

    success, msg = revoke_access_request(access_req)

    if success:
        db.session.commit()
        return jsonify({"message": msg, "status": "revoked"}), 200
    else:
        db.session.rollback()
        return jsonify({"error": msg}), 500

# Tâche cron ou endpoint pour nettoyer les accès expirés
@app.route('/api/acl/cleanup-expired', methods=['POST'])
@require_login
@in_groupe('authentik Admins')
def cleanup_expired():
    removed_count, removed_list = cleanup_expired_requests(AccessRequest, db)
    return jsonify({
        "message": f"{removed_count} accès expirés nettoyés",
        "removed_count": removed_count,
        "removed": removed_list
    }), 200
"""