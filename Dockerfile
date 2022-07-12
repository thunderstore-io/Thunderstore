FROM node:12-alpine as builder

WORKDIR /app
COPY ./builder/package.json ./builder/yarn.lock /app/
RUN yarn install --frozen-lockfile
COPY ./builder /app
RUN yarn run build

FROM python:3.9-slim-buster@sha256:a32a3204b2b44f3e7e699e5b4af1a5784b6a9b8a4f4446dbb8a3aa65375a8d7d

LABEL org.opencontainers.image.source="https://github.com/thunderstore-io/Thunderstore"

ENV PYTHONUNBUFFERED 1

ENV DB_CERT_DIR /etc/ssl/private/db-certs/

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl build-essential git \
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
