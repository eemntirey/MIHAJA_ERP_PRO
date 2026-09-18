FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=600 --retries=20 --disable-pip-version-check -r requirements.txt

# Create and use a non-root user
RUN groupadd --system app && useradd --system --gid app --create-home --home-dir /home/app app

# Copy application files from the backend build context
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/scripts ./scripts
COPY backend/instance ./instance
COPY backend/uploads ./uploads
COPY backend/run.py backend/run_socket.py ./

RUN chown -R app:app /app
USER app

EXPOSE 5000

# CMD production (B1) : gunicorn worker 'gthread' — 1 worker obligatoire tant
# que SocketIO n'utilise pas message_queue=redis (événements intra-process).
# simple-websocket (requirements) assure l'upgrade WebSocket en mode threading.
# Dev : conserver `python run.py` (Werkzeug threaded) hors production.
CMD ["gunicorn", "--workers", "1", "--threads", "8", "--worker-class", "gthread", \
     "--bind", "0.0.0.0:5000", "--timeout", "120", "--access-logfile", "-", \
     "app:create_app()"]
