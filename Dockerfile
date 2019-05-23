FROM node:12.2.0-alpine as builder

WORKDIR /app
COPY ./builder/package.json /app/package.json
RUN npm install
COPY ./builder /app
RUN npm run build

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
COPY --from=builder /app/build /app/static_built

RUN SECRET_KEY=x python manage.py collectstatic --noinput

HEALTHCHECK --interval=5s --timeout=8s --retries=3 \
    CMD curl --fail --header "Host: $SERVER_NAME" localhost:8000/healthcheck || exit 1

ENTRYPOINT ["/bin/bash", "/app/docker-entrypoint.sh"]
