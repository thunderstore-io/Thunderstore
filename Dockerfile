FROM node:12.2.0-alpine as builder

WORKDIR /app
COPY ./builder/package.json ./builder/package-lock.json /app/
RUN npm ci
COPY ./builder /app
RUN npm run build

FROM python:3.8.1-slim-buster
ENV PYTHONUNBUFFERED 1
WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY ./django/pyproject.toml ./django/poetry.lock /app/

RUN pip install -U pip poetry==1.0.0 --no-cache-dir && \
    poetry config virtualenvs.create false && \
    poetry install && \
    rm -rf ~/.cache

COPY ./django /app
COPY --from=builder /app/build /app/static_built

RUN SECRET_KEY=x python manage.py collectstatic --noinput

HEALTHCHECK --interval=5s --timeout=8s --retries=3 \
    CMD curl --fail --header "Host: $SERVER_NAME" localhost:8000/healthcheck || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
