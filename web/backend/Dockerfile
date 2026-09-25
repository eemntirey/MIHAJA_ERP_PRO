FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=600 --retries=20 --disable-pip-version-check -r requirements.txt \
    && python -c "import barcode; print('python-barcode OK')"

# Create and use a non-root user
RUN groupadd --system app && useradd --system --gid app --create-home --home-dir /home/app app

# Copy application files from the backend build context
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/scripts ./scripts
# instance/ et uploads/ sont gitignorés : créer les dossiers à vide
# (sinon COPY échoue si le dossier n'existe pas dans le build context)
RUN mkdir -p ./instance ./uploads
COPY backend/run.py backend/run_socket.py ./

RUN chown -R app:app /app
USER app

EXPOSE 5000

# Bootstrap PostgreSQL automatique avant Gunicorn.
# Une base vide est initialisee; une base partielle/incoherente bloque le demarrage
# sans suppression ni reinitialisation de donnees.
CMD ["sh", "-c", "python scripts/bootstrap_production.py && exec gunicorn --workers 1 --threads 8 --worker-class gthread --bind 0.0.0.0:5000 --timeout 120 --access-logfile - 'app:create_app()'"]
