FROM node:12-alpine as builder

WORKDIR /app
COPY ./builder/package.json ./builder/package-lock.json /app/
RUN npm ci
COPY ./builder /app
RUN npm run build

FROM python:3.8-slim-buster

LABEL org.opencontainers.image.source https://github.com/risk-of-thunder/Thunderstore

ENV PYTHONUNBUFFERED 1

ENV DB_CERT_DIR /etc/ssl/private/db-certs/

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl build-essential cron \
 && rm -rf /var/lib/apt/lists/*

COPY ./web/pyproject.toml ./web/poetry.lock /app/

RUN pip install -U pip poetry~=1.1.4 --no-cache-dir && \
    poetry config virtualenvs.create false && \
    poetry install && \
    rm -rf ~/.cache

COPY --from=builder /app/build /app/static_built
COPY ./web /app

RUN SECRET_KEY=x python manage.py collectstatic --noinput

COPY ./web/crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab

HEALTHCHECK --interval=5s --timeout=8s --retries=3 \
    CMD curl --fail --header "Host: $SERVER_NAME" localhost:8000/healthcheck/ || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
