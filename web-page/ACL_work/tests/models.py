"""
Modèles de base de données pour les demandes d'accès
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class AccessRequest(db.Model):
    """Modèle pour les demandes d'accès aux serveurs"""
    __tablename__ = 'access_requests'

    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), nullable=False, index=True)
    user_name = Column(String(255), nullable=False)
    server_id = Column(String(255), nullable=False)
    server_name = Column(String(255), nullable=False)
    tailscale_tag = Column(String(255))  # Tag Tailscale (ex: "tag:machine-1")
    status = Column(String(50), default='pending', nullable=False)  # pending, approved, denied, expired, revoked
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime)
    approved_by = Column(String(255))
    expires_at = Column(DateTime)  # Pour les accès temporaires (3 jours)
    reason = Column(Text)
    admin_notes = Column(Text)
    acl_applied = Column(Boolean, default=False)  # True si la règle ACL a été ajoutée à Tailscale

    def __repr__(self):
        return f'<AccessRequest {self.user_name} -> {self.server_name}>'

    def is_expired(self):
        """Vérifie si la demande a expiré"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    def approve(self, admin_email):
        """Approuve la demande"""
        self.status = 'approved'
        self.approved_at = datetime.utcnow()
        self.approved_by = admin_email
        self.expires_at = datetime.utcnow() + timedelta(days=3)
        db.session.commit()

    def deny(self, admin_email, notes):
        """Rejette la demande"""
        self.status = 'denied'
        self.approved_at = datetime.utcnow()
        self.approved_by = admin_email
        self.admin_notes = notes
        db.session.commit()

