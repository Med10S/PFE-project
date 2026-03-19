"""
Système d'authentification IAM avec Authentik OAuth2/OIDC
Utilise requests-oauthlib pour une implémentation simplifiée
"""

import os
import requests
from functools import wraps
from flask import session, redirect, url_for, flash, request, current_app
from requests_oauthlib import OAuth2Session

# Configuration pour développement (permet HTTP non sécurisé)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
# Configuration Authentik
_base_url = os.getenv('AUTHENTIK_BASE_URL', '').rstrip('/')

AUTHENTIK_CONFIG = {
    'client_id': os.getenv('AUTHENTIK_CLIENT_ID'),
    'client_secret': os.getenv('AUTHENTIK_CLIENT_SECRET'),
    'base_url': _base_url,
    'authorization_url': os.getenv('AUTHENTIK_AUTHORIZATION_URL', f'{_base_url}/application/o/authorize/'),
    'token_url': os.getenv('AUTHENTIK_TOKEN_URL', f'{_base_url}/application/o/token/'),
    'userinfo_url': os.getenv('AUTHENTIK_USERINFO_URL', f'{_base_url}/application/o/userinfo/'),
    'scope': ['openid', 'profile', 'email', 'groups', 'offline_access', 'permissions'],
    'redirect_uri': os.getenv('AUTHENTIK_REDIRECT_URI', '')
}

class User:
    def __init__(self, username, email, groups, permissions):
        self.username = username
        self.email = email
        self.groups = groups
        self.permissions = permissions
        self.role = self.get_primary_role()
        self.tags = self.get_user_tags()

    def get_primary_role(self):
        """Détermine le rôle principal basé sur les groupes"""
        if 'Admins' in self.groups:
            return 'Admins'
        elif 'read_users' in self.groups:
            return 'read_users'
        else:
            return 'unknown'

    def get_user_tags(self):
        """Mappe les groupes Authentik aux tags Tailscale"""
        tags = []
        group_to_tag_mapping = {
            'dev': 'tag:dev',
            'prod': 'tag:prod',
            'admin': 'tag:admin',
            'read_users': 'tag:user',
            'Admins': 'tag:admin',
        }

        for group in self.groups:
            if group in group_to_tag_mapping:
                tags.append(group_to_tag_mapping[group])

        return tags

def create_oauth_session():
    """Crée une session OAuth2 avec la configuration correcte"""
    return OAuth2Session(
        client_id=AUTHENTIK_CONFIG['client_id'],
        scope=AUTHENTIK_CONFIG['scope'],
        redirect_uri=AUTHENTIK_CONFIG['redirect_uri']
    )

def get_authorization_url():
    """Génère l'URL d'autorisation OAuth2 - Version simplifiée avec requests-oauthlib"""
    oauth = create_oauth_session()
    authorization_url, state = oauth.authorization_url(AUTHENTIK_CONFIG['authorization_url'])
    
    # Stocker le state pour validation lors du callback
    session['oauth_state'] = state
    
    return authorization_url

def exchange_code_for_token(authorization_response):
    """Échange le code d'autorisation contre un access token - Version simplifiée"""
    # Créer la session OAuth2 avec les mêmes paramètres que dans get_authorization_url()
    oauth = OAuth2Session(
        client_id=AUTHENTIK_CONFIG['client_id'],
        state=session.get('oauth_state'),
        redirect_uri=AUTHENTIK_CONFIG['redirect_uri']
    )
    
    # Échanger le code contre des tokens
    token = oauth.fetch_token(
        AUTHENTIK_CONFIG['token_url'],
        client_secret=AUTHENTIK_CONFIG['client_secret'],
        authorization_response=authorization_response
    )
    
    # Nettoyer le state de la session
    session.pop('oauth_state', None)
    
    return token

def get_current_user():
    """Récupère l'utilisateur depuis la session SANS appel réseau"""
    if 'user_data' in session:
        data = session['user_data']
        print(f"Récupération de l'utilisateur depuis la session: {data}")
        return User(
            username=data['username'],
            email=data['email'],
            groups=data['groups'],
            permissions=data['permissions']
        )
    return None

def get_user_info(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        response = requests.get(AUTHENTIK_CONFIG['userinfo_url'], headers=headers, timeout=5)
        if response.status_code != 200:
            return None
        
        user_info = response.json()
        print(f"User info raw from Authentik: {user_info}")
        groups = user_info.get('groups', [])
        
        # Récupération des attributs envoyés par Authentik
        permissions = []
        permissions = user_info.get('permissions', [])  
        # Supprimer les doublons
        permissions = list(set(permissions))
            
        return {
            'username': user_info.get('preferred_username', user_info.get('sub')),
            'email': user_info.get('email', ''),
            'groups': groups,
            'permissions': permissions
        }
    except Exception as e:
        print(f"Erreur: {e}")
        return None

        
def has_permission(permission):
    """Vérifie si l'utilisateur actuel a une permission spécifique"""
    user = get_current_user()
    if user:
        return permission in user.permissions
    return False

def require_login(f):
    """Décorateur qui nécessite une connexion"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            flash('Vous devez vous connecter pour accéder à cette page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def require_permission(permission):
    """Décorateur qui nécessite une permission spécifique"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_permission(permission):
                flash(f'Accès refusé. Permission requise: {permission}', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def in_groupe(groupe):
    """Décorateur qui nécessite un rôle spécifique"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            usergroups = user.groups if user else []
            if groupe not in usergroups:
                flash(f'Accès refusé. Groupe requis: {groupe}', 'error')
                return redirect(url_for('login'))

                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def refresh_access_token():
    """Rafraîchit l'access token en utilisant le refresh token"""
    if 'refresh_token' not in session:
        return False
    
    try:
        oauth = OAuth2Session(
            client_id=AUTHENTIK_CONFIG['client_id'],
            token={'refresh_token': session['refresh_token']}
        )
        
        token = oauth.refresh_token(
            AUTHENTIK_CONFIG['token_url'],
            client_id=AUTHENTIK_CONFIG['client_id'],
            client_secret=AUTHENTIK_CONFIG['client_secret']
        )
        
        session['access_token'] = token['access_token']
        if 'refresh_token' in token:
            session['refresh_token'] = token['refresh_token']
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error refreshing token: {e}")
        return False