"""
Intégration avec les modifications Tailscale ACL
À implémenter après la structure de base
"""

from app import app
import requests
import json


def add_user_to_tailscale_group(user_email, group_name, tailnet):
    """
    Ajoute un utilisateur à un groupe Tailscale via l'API ACL

    Args:
        user_email: Email de l'utilisateur
        group_name: Nom du groupe (ex: "group:prod")
        tailnet: Tailnet ID

    Returns:
        bool: Succès de l'opération
    """
    # TODO: Implémenter
    # 1. GET /api/v2/tailnet/{tailnet}/acl - Récupérer ACL actuelle
    # 2. Modifier la liste d'utilisateurs du groupe
    # 3. POST /api/v2/tailnet/{tailnet}/acl - Enregistrer les modifications
    pass


def remove_user_from_tailscale_group(user_email, group_name, tailnet):
    """
    Retire un utilisateur d'un groupe Tailscale

    Args:
        user_email: Email de l'utilisateur
        group_name: Nom du groupe
        tailnet: Tailnet ID

    Returns:
        bool: Succès de l'opération
    """
    # TODO: Implémenter
    pass


def get_tailscale_acl(tailnet):
    """Récupère la configuration ACL actuelle de Tailscale"""
    # TODO: Implémenter
    # GET /api/v2/tailnet/{tailnet}/acl
    pass


def update_tailscale_acl(acl_config, tailnet):
    """Met à jour la configuration ACL de Tailscale"""
    # TODO: Implémenter
    # POST /api/v2/tailnet/{tailnet}/acl
    pass


# Exemple d'utilisation:
"""
@app.route('/api/access-request/<int:request_id>/approve', methods=['POST'])
@require_login
@in_groupe('authentik Admins')
def approve_and_apply_access(request_id):
    access_req = AccessRequest.query.get(request_id)

    # Approbation
    access_req.approve(current_user.email)

    # Récupérer le groupe associé au serveur
    server_group = get_server_group(access_req.server_id)  # ex: "group:prod"

    # Ajouter l'utilisateur au groupe Tailscale
    success = add_user_to_tailscale_group(
        access_req.user_email,
        server_group,
        TAILSCALE_TAILNET
    )

    if success:
        return jsonify({"message": "Accès approuvé et appliqué"})
    else:
        access_req.status = "error"
        db.session.commit()
        return jsonify({"error": "Erreur lors de l'application de l'accès"}), 500
"""
