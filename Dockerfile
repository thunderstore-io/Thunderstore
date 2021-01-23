FROM node:14-alpine as builder

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
    curl build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY ./django/pyproject.toml ./django/poetry.lock /app/

RUN pip install -U pip poetry~=1.1.4 --no-cache-dir && \
    poetry config virtualenvs.create false && \
    poetry install && \
    rm -rf ~/.cache

COPY --from=builder /app/build /app/static_built
COPY ./django /app

RUN SECRET_KEY=x python manage.py collectstatic --noinput

HEALTHCHECK --interval=5s --timeout=8s --retries=3 \
    CMD python readycheck.py || exit 1

ENTRYPOINT ["python", "/app/docker_entrypoint.py"]
