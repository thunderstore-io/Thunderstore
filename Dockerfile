FROM node:12-alpine as builder

WORKDIR /app
COPY ./builder/package.json ./builder/yarn.lock /app/
RUN yarn install --frozen-lockfile
COPY ./builder /app
RUN yarn run build

FROM python:3.8-slim-buster@sha256:2516c4bc037b8144b6104e73e6bdd0c861725d9ed7bd05095dded22842991508

LABEL org.opencontainers.image.source="https://github.com/thunderstore-io/Thunderstore"

ARG BUILD_INSTALL_EXTRAS

ENV PYTHONUNBUFFERED 1

ENV DB_CERT_DIR /etc/ssl/private/db-certs/

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl build-essential git \
 && rm -rf /var/lib/apt/lists/*

COPY ./flake8-thunderstore/ /flake8-thunderstore
COPY ./python-packages/ /python-packages
COPY ./django/pyproject.toml ./django/poetry.lock /app/

RUN pip install -U pip setuptools wheel virtualenv==20.7.2 poetry~=1.4.2 --no-cache-dir && \
    poetry config virtualenvs.create false && \
    poetry config installer.max-workers 1 && \
    if [ $BUILD_INSTALL_EXTRAS = true ] ; then \
      poetry install --with plugins ; \
    else \
      poetry install ; \
    fi && \
    rm -rf ~/.cache

COPY --from=builder /app/build /app/static_built
COPY ./django /app

RUN SECRET_KEY=x python manage.py collectstatic --noinput

HEALTHCHECK --interval=5s --timeout=8s --retries=3 \
    CMD python readycheck.py || exit 1

ENTRYPOINT ["python", "/app/docker_entrypoint.py"]
