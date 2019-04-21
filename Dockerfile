FROM python:3.7.0-slim-stretch
ENV PYTHONUNBUFFERED 1
WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY ./django/requirements.txt ./django/requirements-dev.txt /app/

RUN pip install -U pip --no-cache-dir && \
    pip install -r requirements.txt -r requirements-dev.txt --no-cache-dir

COPY ./django /app

RUN SECRET_KEY=x python manage.py collectstatic --noinput

HEALTHCHECK --interval=5s --timeout=3s --retries=3 \
    CMD curl --fail localhost:8000/healthcheck || exit 1

ENTRYPOINT ["/bin/bash", "/app/docker-entrypoint.sh"]
