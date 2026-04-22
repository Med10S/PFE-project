"""
Journalisation d'audit applicative (format clé=valeur) pour Wazuh.
"""

import logging
import os
from typing import Any

AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "/app/logs/security_audit.log")
_LOGGER_NAME = "pfe_audit"


def _escape(value: Any) -> str:
    raw = "-" if value is None else str(value)
    return raw.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ").replace("\r", " ")


def _get_audit_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_dir = os.path.dirname(AUDIT_LOG_PATH)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(AUDIT_LOG_PATH)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def emit_audit_event(
    event: str,
    status: str,
    user_email: str = "-",
    user_name: str = "-",
    actor_email: str = "-",
    ip: str = "-",
    server_id: str = "-",
    server_name: str = "-",
    request_id: Any = "-",
    reason: str = "-",
    ttl: str = "-",
    message: str = "-",
) -> None:
    fields = {
        "event": event,
        "status": status,
        "user_email": user_email,
        "user_name": user_name,
        "actor_email": actor_email,
        "ip": ip,
        "server_id": server_id,
        "server_name": server_name,
        "request_id": request_id,
        "reason": reason,
        "ttl": ttl,
        "message": message,
    }

    payload = " ".join(f'{key}="{_escape(value)}"' for key, value in fields.items())
    _get_audit_logger().info("PFE_AUDIT %s", payload)
