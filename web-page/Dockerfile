FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    cron \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY ./requirements.txt .

# Installer pip tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY ./ .

# Créer les répertoires de logs
RUN mkdir -p logs scripts

# Configurer le cron job d'expiration des accès (toutes les 6 heures)
RUN touch /app/logs/cron.log \
    && echo 'SHELL=/bin/sh' > /etc/cron.d/expire-access \
    && echo 'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' >> /etc/cron.d/expire-access \
    && echo '0 */6 * * * root . /etc/environment; cd /app && /usr/local/bin/python3 /app/scripts/expire_access.py >> /app/logs/cron.log 2>&1' >> /etc/cron.d/expire-access \
    && chmod 0644 /etc/cron.d/expire-access \
    && crontab /etc/cron.d/expire-access \
    && apt-get install -y --no-install-recommends apt-transport-https \
    && curl -fsSL https://packages.wazuh.com/key/GPG-KEY-WAZUH \
    | gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import \
    && chmod 644 /usr/share/keyrings/wazuh.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" > /etc/apt/sources.list.d/wazuh.list \
    && apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 update \
    && apt-get install -y --no-install-recommends --fix-missing wazuh-agent 

# Exposer le port
EXPOSE 5000

# Lancer cron + application Flask
CMD ["sh", "-c", "printenv > /etc/environment && cron && python3 app.py"]
