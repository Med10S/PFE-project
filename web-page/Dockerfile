FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
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

# Exposer le port
EXPOSE 5000

# Lancer l'application
CMD ["python3", "app.py"]
