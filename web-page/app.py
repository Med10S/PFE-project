"""
Application Web Flask avec authentification Authentik IAM et tableau de bord
"""

from http import server

from xmlrpc import server

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from auth import (
    get_current_user, require_login, require_permission, in_groupe,
    get_authorization_url, exchange_code_for_token, get_user_info, refresh_access_token
)
from models import db, AccessRequest
import os
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import inspect, text, or_
from ACL_work.tailscale_acl_api import (
    approve_access_request,
    revoke_access_request,
    cleanup_expired_requests
)
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') 
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)


db_user = os.getenv('POSTGRES_USER',)
db_password = os.getenv('POSTGRES_PASSWORD',)
db_host = os.getenv('POSTGRES_HOST', )  
db_port = os.getenv('POSTGRES_PORT', )
db_name = os.getenv('POSTGRES_DB',)

DATABASE_URL = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

_schema_checked = False


def ensure_access_requests_schema():
    """Ajoute les colonnes manquantes sur access_requests si le schéma est ancien."""
    engine = db.engine
    inspector = inspect(engine)

    if not inspector.has_table('access_requests'):
        db.create_all()
        return

    existing_columns = {col['name'] for col in inspector.get_columns('access_requests')}
    required_columns = {
        'user_email': 'VARCHAR(255)',
        'user_name': 'VARCHAR(255)',
        'server_id': 'VARCHAR(255)',
        'server_name': 'VARCHAR(255)',
        'tailscale_tag': 'VARCHAR(255)',
        'status': "VARCHAR(50) DEFAULT 'pending'",
        'requested_at': 'TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP',
        'approved_at': 'TIMESTAMP WITHOUT TIME ZONE',
        'approved_by': 'VARCHAR(255)',
        'expires_at': 'TIMESTAMP WITHOUT TIME ZONE',
        'reason': 'TEXT',
        'admin_notes': 'TEXT',
        'acl_applied': 'BOOLEAN DEFAULT FALSE',
    }

    missing_columns = [
        (column_name, column_def)
        for column_name, column_def in required_columns.items()
        if column_name not in existing_columns
    ]

    if not missing_columns:
        return

    with engine.begin() as conn:
        for column_name, column_def in missing_columns:
            conn.execute(text(
                f"ALTER TABLE access_requests ADD COLUMN IF NOT EXISTS {column_name} {column_def}"
            ))


@app.before_request
def ensure_schema_once():
    """Vérifie le schéma au premier hit, y compris en mode WSGI (gunicorn/uwsgi)."""
    global _schema_checked
    if _schema_checked:
        return

    ensure_access_requests_schema()
    _schema_checked = True

# Configuration des sessions
app.config['SESSION_TYPE'] = 'filesystem'

# Configuration Tailscale API
TAILSCALE_API_TOKEN = os.getenv('TAILSCALE_API_TOKEN', '')
TAILSCALE_TAILNET = os.getenv('TAILSCALE_TAILNET', '')
TAILSCALE_BASE_URL = 'https://api.tailscale.com/api/v2'

# ===== Fonctions utilitaires Tailscale =====
def get_tailscale_headers():
    """Retourne les headers pour les requêtes Tailscale API"""
    return {
        'Authorization': f'Bearer {TAILSCALE_API_TOKEN}',
        'Content-Type': 'application/json'
    }

def get_tailscale_devices():
    """Récupère tous les devices/machines de Tailscale avec leurs tags"""
    try:
        url = f"{TAILSCALE_BASE_URL}/tailnet/{TAILSCALE_TAILNET}/devices"
        response = requests.get(url, headers=get_tailscale_headers(), timeout=10)
        if response.status_code == 200:
            devices = response.json().get('devices', [])
            return [
                {
                    'id': device.get('id'),
                    'name': device.get('name'),
                    'hostname': device.get('hostname'),
                    'user': device.get('user'),
                    'addresses': device.get('addresses', []),
                    'tags': device.get('tags', []),
                    'status': 'en ligne' if device.get('connectedToControl') else 'hors ligne',
                    'os': device.get('os'),
                    'lastSeen': device.get('lastSeen'),
                }
                for device in devices
            ]
        return []
    except Exception as e:
        print(f"Erreur lors de la récupération des devices: {e}")
        return []

def get_tailscale_users():
    """Récupère tous les utilisateurs de Tailscale"""
    try:
        url = f"{TAILSCALE_BASE_URL}/tailnet/{TAILSCALE_TAILNET}/users"
        response = requests.get(url, headers=get_tailscale_headers(), timeout=10)
        if response.status_code == 200:
            users = response.json().get('users', [])
            return [
                {
                    'id': user.get('id'),
                    'displayName': user.get('displayName'),
                    'loginName': user.get('loginName'),
                    'role': user.get('role'),
                    'status': user.get('status'),
                    'deviceCount': user.get('deviceCount'),
                    'currentlyConnected': user.get('currentlyConnected'),
                }
                for user in users
            ]
        return []
    except Exception as e:
        print(f"Erreur lors de la récupération des utilisateurs: {e}")
        return []

def filter_devices_by_user_tags(devices, user_tags):
    """Filtre les devices en fonction des tags de l'utilisateur"""
    accessible = []
    not_accessible = []

    for device in devices:
        device_tags = set(device.get('tags', []))
        user_tags_set = set(user_tags)

        if device_tags & user_tags_set:  # Intersection
            accessible.append(device)
        else:
            not_accessible.append(device)

    return accessible, not_accessible

@app.route('/')
@require_login
def index():
    user = get_current_user() 
    print(f"Accès à l'index pour {user.username} avec rôle {user.groups} et permissions {user.permissions}")
    if user:
        if 'authentik Admins' in user.groups:
            print(f"Redirection vers le dashboard admin pour {user.username}")
            return redirect(url_for('admin_dashboard'))
        if 'dev' in user.groups:
            return redirect(url_for('user_dashboard'))
    # Si pas d'utilisateur valide ou rôle inconnu, on nettoie TOUT et on va au login
    session.clear()
    flash(f"Connexion réussie, mais aucun rôle valide assigné pour {user.username}", 'warning')
    return redirect(url_for('login'))

def _is_valid_webfinger_resource(resource: str) -> bool:
    if resource.startswith('acct:'):
        return re.match(r'^acct:[^@\s]+@[^@\s]+$', resource) is not None
    parsed = urlparse(resource)
    return bool(parsed.scheme and parsed.netloc)


@app.route('/.well-known/webfinger', methods=['GET'])
def webfinger():
    resource = request.args.get('resource', '').strip()
    requested_rels = request.args.getlist('rel')

    subject = os.getenv('WEBFINGER_SUBJECT')
    issuer_href = os.getenv(
        'WEBFINGER_ISSUER',
        'https://authentik.sbihi.tech/application/o/tailscale/'
    )
    issuer_rel = 'http://openid.net/specs/connect/1.0/issuer'

    if not resource or not _is_valid_webfinger_resource(resource):
        response = jsonify({'error': 'invalid_request', 'error_description': 'resource parameter is required and must be a valid URI'})
        response.status_code = 400
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.mimetype = 'application/jrd+json'
        return response

    accepted_resources = {subject}
    if subject.startswith('acct:'):
        accepted_resources.add(subject[len('acct:'):])

    if resource not in accepted_resources:
        response = jsonify({'error': 'not_found', 'error_description': 'No information available for this resource'})
        response.status_code = 404
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.mimetype = 'application/jrd+json'
        return response

    links = [{'rel': issuer_rel, 'href': issuer_href}]
    if requested_rels:
        links = [link for link in links if link['rel'] in requested_rels]

    response = jsonify({'subject': subject, 'links': links})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.mimetype = 'application/jrd+json'
    return response

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
        "https://authentik.sbihi.tech/application/o/portail-interne/end-session/?"
        f"post_logout_redirect_uri={url_for('login', _external=True)}"
    )
    return redirect(authentik_logout_url)
@app.route('/admin/dashboard')
@require_login
@in_groupe('authentik Admins')
def admin_dashboard():
    """Dashboard pour les administrateurs"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    users = get_tailscale_users()
    devices = get_tailscale_devices()

    print(f"Accès au dashboard admin pour {user.username} avec rôle {user.role} et permissions {user.permissions}")
    return render_template('admin_dashboard.html',
                         user=user,
                         users=users,
                         servers=devices)

@app.route('/user/dashboard')
@require_login
def user_dashboard():
    """Dashboard pour les utilisateurs en lecture seule"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    devices = get_tailscale_devices()

    # Récupérer les demandes de l'utilisateur depuis la DB.
    now = datetime.utcnow()
    pending_request = AccessRequest.query.filter_by(
        user_email=user.email,
        status='pending'
    ).order_by(AccessRequest.requested_at.desc()).first()

    approved_access_requests = AccessRequest.query.filter(
        AccessRequest.user_email == user.email,
        AccessRequest.status == 'approved',
        or_(AccessRequest.expires_at == None, AccessRequest.expires_at > now)
    ).order_by(AccessRequest.expires_at.asc()).all()

    approved_server_ids = {req.server_id for req in approved_access_requests}

    # Accès autorisé si tag en commun OU accès ACL approuvé en DB.
    accessible_devices = []
    not_accessible_devices = []
    user_tags_set = set(user.tags)
    for device in devices:
        device_tags = set(device.get('tags', []))
        has_tag_access = bool(device_tags & user_tags_set)
        has_acl_access = device.get('id') in approved_server_ids

        if has_tag_access or has_acl_access:
            accessible_devices.append(device)
        else:
            not_accessible_devices.append(device)

    return render_template('user_dashboard.html',
                         user=user,
                         accessible_devices=accessible_devices,
                         not_accessible_devices=not_accessible_devices,
                         pending_request=pending_request,
                         has_pending_request=bool(pending_request),
                         approved_access_requests=approved_access_requests)

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
    """API pour récupérer la liste des utilisateurs Tailscale"""
    users = get_tailscale_users()
    return jsonify(users)

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_login
@require_permission('users:update')
def api_update_user(user_id):
    """API pour mettre à jour un utilisateur via Tailscale"""
    # Cette route peut appeler l'API Tailscale pour mettre à jour les utilisateurs
    data = request.get_json()
    return jsonify({"message": "Utilisateur mis à jour avec succès", "user_id": user_id})

@app.route('/api/servers')
@require_login
@require_permission('servers:manage')
def api_servers():
    """API pour récupérer la liste des serveurs/devices Tailscale"""
    devices = get_tailscale_devices()
    return jsonify(devices)

@app.route('/api/servers/<int:server_id>/restart', methods=['POST'])
@require_login
@require_permission('servers:manage')
def api_restart_server(server_id):
    """API pour demander accès à un serveur"""
    # Cette route peut être modifiée pour appeler l'API Tailscale
    # ou pour enregistrer une demande dans la DB
    return jsonify({"message": "Demande d'accès enregistrée", "server_id": server_id})

@app.route('/api/refresh-token', methods=['POST'])
@require_login
def api_refresh_token():
    """API pour rafraîchir le token d'accès"""
    if refresh_access_token():
        return jsonify({"message": "Token rafraîchi avec succès"})
    else:
        return jsonify({"error": "Impossible de rafraîchir le token"}), 401

# ===== Routes d'administration des demandes d'accès =====
@app.route('/admin/access-requests')
@require_login
@in_groupe('authentik Admins')
def admin_access_requests():
    """Dashboard pour gérer les demandes d'accès"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    # Récupérer toutes les demandes
    pending = AccessRequest.query.filter_by(status='pending').all()
    approved = AccessRequest.query.filter_by(status='approved').all()
    denied = AccessRequest.query.filter_by(status='denied').all()

    return render_template('admin_access_requests.html',
                         user=user,
                         pending_requests=pending,
                         approved_requests=approved,
                         denied_requests=denied)

@app.route('/api/access-request/<int:request_id>/approve', methods=['POST'])
@require_login
@in_groupe('authentik Admins')
def api_approve_request(request_id):
    """Approuver une demande d'accès"""
    user = get_current_user()
    access_req = AccessRequest.query.get(request_id)

    if not access_req:
        return jsonify({"error": "Demande non trouvée"}), 404

    access_req.approve(user.email)
    tailscale_tag = access_req.tailscale_tag
    success, msg = approve_access_request(access_req, "mohammed.sbihi@sbihi.tech", tailscale_tag)

    if success:
        db.session.commit()  # Important!
        print(f"✓ Succès: {msg}")
        
    else:
        db.session.rollback()
        print(f"✗ Erreur: {msg}")

    return jsonify({
        "message": "Demande approuvée avec succès",
        "expires_at": access_req.expires_at.isoformat()
    })

@app.route('/api/access-request/<int:request_id>/deny', methods=['POST'])
@require_login
@in_groupe('authentik Admins')
def api_deny_request(request_id):
    """Rejetter une demande d'accès"""
    user = get_current_user()
    data = request.get_json()
    notes = data.get('notes', '')

    access_req = AccessRequest.query.get(request_id)

    if not access_req:
        return jsonify({"error": "Demande non trouvée"}), 404

    access_req.deny(user.email, notes)

    return jsonify({"message": "Demande rejetée avec succès"})

@app.route('/api/access-requests')
@require_login
@in_groupe('authentik Admins')
def api_access_requests():
    """API pour récupérer toutes les demandes d'accès"""
    pending = AccessRequest.query.filter_by(status='pending').all()
    approved = AccessRequest.query.filter_by(status='approved').all()
    denied = AccessRequest.query.filter_by(status='denied').all()

    return jsonify({
        "pending": [
            {
                "id": r.id,
                "user_name": r.user_name,
                "user_email": r.user_email,
                "server_name": r.server_name,
                "requested_at": r.requested_at.isoformat()
            }
            for r in pending
        ],
        "approved": [
            {
                "id": r.id,
                "user_name": r.user_name,
                "server_name": r.server_name,
                "approved_at": r.approved_at.isoformat(),
                "expires_at": r.expires_at.isoformat() if r.expires_at else None
            }
            for r in approved
        ],
        "denied": [
            {
                "id": r.id,
                "user_name": r.user_name,
                "server_name": r.server_name,
                "denied_at": r.approved_at.isoformat(),
                "notes": r.admin_notes
            }
            for r in denied
        ]
    })
@app.route('/api/request-access', methods=['POST'])
@require_login
def api_request_access():
    """API pour demander accès à un serveur"""
    data = request.get_json()
    server_id = data.get('server_id')
    user = get_current_user()

    if not server_id or not user:
        return jsonify({"error": "Données manquantes"}), 400

    # Bloquer toute nouvelle demande tant qu'une demande est en attente.
    pending_request = AccessRequest.query.filter_by(
        user_email=user.email,
        status='pending'
    ).order_by(AccessRequest.requested_at.desc()).first()
    if pending_request:
        return jsonify({
            "error": "Vous avez déjà une demande en attente",
            "pending_request": {
                "id": pending_request.id,
                "server_name": pending_request.server_name,
                "requested_at": pending_request.requested_at.isoformat()
            }
        }), 400

    # Récupère les informations du serveur
    devices = get_tailscale_devices()
    server = next((d for d in devices if d['id'] == server_id), None)
    if not server:
        return jsonify({"error": "Serveur non trouvé"}), 404

    # Empêcher la demande si l'utilisateur a déjà accès (tag ou ACL approuvée active).
    server_tags = set(server.get('tags', []))
    has_tag_access = bool(server_tags & set(user.tags))
    now = datetime.utcnow()
    has_acl_access = AccessRequest.query.filter(
        AccessRequest.user_email == user.email,
        AccessRequest.server_id == server_id,
        AccessRequest.status == 'approved',
        or_(AccessRequest.expires_at == None, AccessRequest.expires_at > now)
    ).first() is not None
    if has_tag_access or has_acl_access:
        return jsonify({"error": "Vous avez déjà accès à ce serveur"}), 400

    # Vérifier si une demande existe déjà
    existing_request = AccessRequest.query.filter_by(
        user_email=user.email,
        server_id=server_id,
        status='pending'
    ).first()

    if existing_request:
        return jsonify({"error": "Une demande est déjà en cours pour ce serveur"}), 400
    
    
    tags = server.get('tags', [])
    matching_machine_tags = [
        tag for tag in tags
        if tag.startswith("tag:machine-") and len(tag) > len("tag:machine-")
    ]

    if len(matching_machine_tags) > 1:
        return jsonify({
            "error": "Plusieurs tags machine détectés pour ce serveur",
            "tags": matching_machine_tags
        }), 400

    tailscale_tag = matching_machine_tags[0] if matching_machine_tags else None

    # Créer une nouvelle demande
    access_request = AccessRequest(
        user_email=user.email,
        user_name=user.username,
        server_id=server_id,
        server_name=server.get('name', server_id),
        tailscale_tag=tailscale_tag
    )

    try:
        db.session.add(access_request)
        db.session.commit()

        return jsonify({
            "message": "Demande d'accès enregistrée avec succès",
            "user": user.username,
            "server_id": server_id,
            "request_id": access_request.id
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de l'enregistrement de la demande: {e}")
        return jsonify({"error": "Erreur lors de l'enregistrement de la demande"}), 500

if __name__ == '__main__':
    with app.app_context():
        # Créer les tables si elles n'existent pas
        db.create_all()

    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    use_ssl = os.getenv('FLASK_USE_SSL', 'false').lower() == 'true'

    if use_ssl:
        cert_file = os.getenv('SSL_CERT_FILE', '/etc/ssl/myapp/fullchain.pem')
        key_file = os.getenv('SSL_KEY_FILE', '/etc/ssl/myapp/private.key')
        app.run(debug=True, host=host, port=port, ssl_context=(cert_file, key_file))
    else:
        app.run(debug=True, host=host, port=port)