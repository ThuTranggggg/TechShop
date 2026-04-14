FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY . /app

EXPOSE 8002

CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:${SERVICE_PORT:-8002} --workers 2 --timeout 120"]
