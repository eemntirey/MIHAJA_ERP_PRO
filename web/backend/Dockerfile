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

CMD ["python", "run.py"]