"""
Application Web Flask avec authentification Authentik IAM et tableau de bord
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from auth import (
    get_current_user, require_login, require_permission, require_role,
    get_authorization_url, exchange_code_for_token, get_user_info, refresh_access_token
)
import os
from authlib.integrations.flask_client import OAuth
app = Flask(__name__)
app.secret_key = 'EVXFENKv6NESy84NkroEE48xONAyDcEa0UZ4jFkqIp42owAijeA93rsWDEjA8aVvzSqm9zNPvuEkhjSrGlac2OliaZw9R5AiELtc0PQC0jHnBFMFDHHQ0Hikx0vrQiOv'  # À changer en production

# Configuration des sessions
app.config['SESSION_TYPE'] = 'filesystem'
oauth = OAuth(app)
# Enregistrement du client authentik
oauth.register(
    name='authentik',
    client_id='gyPvmpWdpbjOyk0iaP5hfobyfTCHlfKLinFOV4B4',
    client_secret='EVXFENKv6NESy84NkroEE48xONAyDcEa0UZ4jFkqIp42owAijeA93rsWDEjA8aVvzSqm9zNPvuEkhjSrGlac2OliaZw9R5AiELtc0PQC0jHnBFMFDHHQ0Hikx0vrQiOv',
    server_metadata_url='http://localhost:9090/application/o/portail-interne/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email',
    }
)
# Données simulées pour les fonctionnalités
USERS_LIST = [
    {"id": 1, "username": "admin", "email": "admin@example.com", "role": "Admins", "status": "actif"},
    {"id": 2, "username": "john", "email": "john@example.com", "role": "read_users", "status": "actif"},
    {"id": 3, "username": "marie", "email": "marie@example.com", "role": "read_users", "status": "actif"},
    {"id": 4, "username": "supervisor", "email": "super@example.com", "role": "Admins", "status": "actif"},
]

SERVERS_LIST = [
    {"id": 1, "name": "Web Server 01", "status": "en ligne", "cpu": "45%", "memory": "67%"},
    {"id": 2, "name": "Database Server", "status": "en ligne", "cpu": "23%", "memory": "54%"},
    {"id": 3, "name": "API Server", "status": "maintenance", "cpu": "12%", "memory": "34%"},
    {"id": 4, "name": "Backup Server", "status": "en ligne", "cpu": "8%", "memory": "28%"},
]

@app.route('/')
def index():
    user = get_current_user() 
    if user:
        if user.role == 'Admins':
            return redirect(url_for('admin_dashboard'))
        if user.role == 'read_users':
            return redirect(url_for('user_dashboard'))

    # Si pas d'utilisateur valide ou rôle inconnu, on nettoie TOUT et on va au login
    session.clear()
    flash('Connexion réussie, mais aucun rôle valide assigné.', 'warning')
    return redirect(url_for('login'))

@app.route('/login')
def login():
    # On ne redirige vers l'index QUE si user_data existe déjà en session
    if 'user_data' in session:
        return redirect(url_for('index'))
    
    # Sinon on affiche la page avec le bouton de connexion
    auth_url = get_authorization_url()
    return render_template('login_authentik.html', auth_url=auth_url)
@app.route('/auth/callback')
def auth_callback():
    try:
        # Échange le code contre un token
        token_data = exchange_code_for_token(request.url)
        session['access_token'] = token_data['access_token']
        
        # Récupère les infos UNE SEULE FOIS
        user_info = get_user_info(token_data['access_token'])
        print(f"User Info: {user_info}")
        
        # Ajout du print de debug pour vérifier les groupes
        print(f"User groups from Authentik: {user_info.get('groups')}")

        # Stocke les infos essentielles en session
        session['user_data'] = user_info
        
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Erreur callback: {e}")
        session.clear() # Nettoie tout pour éviter la boucle
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    # Redirection vers Authentik pour fermer la session globale
    # L'URL dépend de votre configuration, souvent : /application/o/portail-interne/end-session/
    authentik_logout_url = (
        "http://localhost:9090/application/o/portail-interne/end-session/?"
        f"post_logout_redirect_uri={url_for('login', _external=True)}"
    )
    return redirect(authentik_logout_url)
@app.route('/admin/dashboard')
@require_login
@require_role('Admins')
def admin_dashboard():
    """Dashboard pour les administrateurs"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    print(f"Accès au dashboard admin pour {user.username} avec rôle {user.role} et permissions {user.permissions}")
    return render_template('admin_dashboard.html', 
                         user=user, 
                         users=USERS_LIST, 
                         servers=SERVERS_LIST)

@app.route('/user/dashboard')
@require_login
@require_role('read_users')
def user_dashboard():
    """Dashboard pour les utilisateurs en lecture seule"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    return render_template('user_dashboard.html', 
                         user=user, 
                         users=USERS_LIST)

@app.route('/profile')
@require_login
def profile():
    """Profil utilisateur"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    return render_template('profile.html', user=user)

@app.route('/api/users')
@require_login
@require_permission('users:read')
def api_users():
    """API pour récupérer la liste des utilisateurs"""
    return jsonify(USERS_LIST)

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_login
@require_permission('users:update')
def api_update_user(user_id):
    """API pour mettre à jour un utilisateur"""
    data = request.get_json()
    # Simulation de mise à jour
    for user in USERS_LIST:
        if user['id'] == user_id:
            user.update(data)
            return jsonify({"message": "Utilisateur mis à jour avec succès", "user": user})
    return jsonify({"error": "Utilisateur non trouvé"}), 404

@app.route('/api/servers')
@require_login
@require_permission('servers:manage')
def api_servers():
    """API pour récupérer la liste des serveurs"""
    return jsonify(SERVERS_LIST)

@app.route('/api/servers/<int:server_id>/restart', methods=['POST'])
@require_login
@require_permission('servers:manage')
def api_restart_server(server_id):
    """API pour redémarrer un serveur"""
    for server in SERVERS_LIST:
        if server['id'] == server_id:
            server['status'] = 'redémarrage en cours'
            return jsonify({"message": f"Serveur {server['name']} en cours de redémarrage"})
    return jsonify({"error": "Serveur non trouvé"}), 404

@app.route('/api/refresh-token', methods=['POST'])
@require_login
def api_refresh_token():
    """API pour rafraîchir le token d'accès"""
    if refresh_access_token():
        return jsonify({"message": "Token rafraîchi avec succès"})
    else:
        return jsonify({"error": "Impossible de rafraîchir le token"}), 401

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)