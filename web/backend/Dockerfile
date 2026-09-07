FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Requirements live at web/requirements.txt when build context is web/
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

RUN groupadd --system app && useradd --system --gid app --create-home --home-dir /home/app app

# Application code
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/scripts ./scripts
COPY backend/run.py backend/run_socket.py backend/manage.py ./
COPY backend/alembic.ini ./alembic.ini

RUN mkdir -p uploads logs instance \
    && chown -R app:app /app

USER app

EXPOSE 5000

# Prefer migrations over create_all — entrypoint can run upgrade when ready
CMD ["python", "run.py"]
