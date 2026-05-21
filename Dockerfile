FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs

# Collect static files
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    SECRET_KEY=build-placeholder \
    DB_NAME=x DB_USER=x DB_PASSWORD=x DB_HOST=x \
    REDIS_URL=redis://x:6379/0 \
    CELERY_BROKER_URL=redis://x:6379/1 \
    CELERY_RESULT_BACKEND=redis://x:6379/2 \
    AMOCRM_DOMAIN=x AMOCRM_CLIENT_ID=x AMOCRM_CLIENT_SECRET=x \
    ANTHROPIC_API_KEY=x \
    python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--workers", "3"]
