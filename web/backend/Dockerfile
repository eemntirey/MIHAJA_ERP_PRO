FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create and use a non-root user
RUN groupadd --system app && useradd --system --gid app --create-home --home-dir /home/app app

# Copy only what is required to run the application (no .env, no logs, no venv).
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY instance ./instance
COPY uploads ./uploads
COPY run.py run_socket.py ./

RUN chown -R app:app /app
USER app

EXPOSE 5000

CMD ["python", "run.py"]