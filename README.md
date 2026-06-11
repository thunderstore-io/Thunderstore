# Thunderstore

[![codecov](https://codecov.io/gh/thunderstore-io/Thunderstore/branch/master/graph/badge.svg)](https://codecov.io/gh/thunderstore-io/Thunderstore)

Thunderstore is a mod database and API for downloading mods. This repository holds
the **Django backend**, the REST API, and the legacy
web UI. The new web frontend lives in a separate repository,
[thunderstore-ui](https://github.com/thunderstore-io/thunderstore-ui).

## Contents

-   [Getting started](#getting-started)
-   [How the dev environment works](#how-the-dev-environment-works)
-   [Running the frontend](#running-the-frontend)
-   [Everyday tasks](#everyday-tasks)
-   [Testing](#testing)
-   [Production configuration](#production-configuration)
-   [License](#license)

## Getting started

You need [Docker](https://docs.docker.com/get-docker/) with Docker Compose.

1. **Configure the environment.** Copy the template and adjust if needed:

    ```bash
    cp .env.template .env
    ```

    If you have the `python-packages` submodule cloned and want its extras, set
    `BUILD_INSTALL_EXTRAS=true` (only the literal value `true` works). Changing it
    later requires a rebuild with `docker compose build`.

2. **Start the backend:**

    ```bash
    docker compose up -d
    ```

3. **Seed the database.** This runs migrations, populates test data, creates the
   site mappings, and creates a default `admin` / `admin` superuser:

    ```bash
    docker compose exec django python manage.py setup_dev_env
    ```

    > **Existing database?** Re-run `setup_dev_env` after pulling a change to
    > the dev domains: it resets the `Site` and `CommunitySite` mappings to the
    > `*.localhost` domains described below (pass `--skip-test-data` to keep
    > your existing data). A database from an older setup lacks these mappings,
    > which surfaces as broken community pages on the legacy site — re-running
    > the command replaces any manual Django-admin cleanup.

The backend is now ready. You can open:

-   **Legacy site** — <http://old.thunderstore.localhost> (works with just the backend)
-   **Admin panel** — <http://thunderstore.localhost/djangoadmin/> (log in with `admin` / `admin`)
-   **Main site** — <http://thunderstore.localhost> (needs the frontend running, see
    [Running the frontend](#running-the-frontend))

Run `docker compose logs -f` to follow the logs.

## How the dev environment works

nginx listens on **port 80** and is the single entry point. It routes by hostname:

-   **`thunderstore.localhost`** — the new main site (Cyberstorm Remix, codenamed
    Nimbus). nginx proxies app routes to the Remix dev server and serves Django's
    `/api`, `/auth`, `/djangoadmin`, `/media`, `/static`, … on the **same origin**,
    so server-side rendering and the browser share one API origin.
-   **`old.thunderstore.localhost`** — the legacy, fully Django-rendered site
    (mirrors the production `old.` domain).

Django does not publish a host port of its own; it is reached only through nginx
(internally on `:8000`).

> Visiting <http://thunderstore.localhost> with **only** the backend running
> shows a "Frontend dev server not running" hint page (HTTP 503) — nginx has no
> frontend dev server to proxy to yet. Start the frontend (below), or use the
> legacy site.

## Running the frontend

The frontend
([thunderstore-ui](https://github.com/thunderstore-io/thunderstore-ui)) runs
**natively** on the host in development — it is faster than running it in a
container, and nginx reaches it at `host.docker.internal:3000`. Clone it next to
this repository and start it:

```bash
git clone https://github.com/thunderstore-io/thunderstore-ui
cd thunderstore-ui
yarn install
yarn dev
```

`yarn dev` runs the Remix dev server on `:3000` together with the build watchers
for the `@thunderstore/cyberstorm`, `@thunderstore/cyberstorm-theme`, and
`@thunderstore/ts-uploader` packages, so edits to the app **and** those packages
hot-reload. With the backend running, the app is served at
<http://thunderstore.localhost> (and directly on <http://localhost:3000>). See
`apps/cyberstorm-remix/README.md` in the thunderstore-ui repo for more detail.

> **Windows:** `*.localhost` hostnames do not resolve automatically. Add these
> entries to `C:\Windows\System32\drivers\etc\hosts`:
>
> ```text
> 127.0.0.1 thunderstore.localhost
> 127.0.0.1 old.thunderstore.localhost
> 127.0.0.1 auth.thunderstore.localhost
> ```
>
> **WSL2:** if you run `yarn dev` inside WSL2 while Docker Desktop runs the
> backend, nginx's `host.docker.internal` reaches the **Windows** host — not
> the WSL2 VM — so the main site shows the "Frontend dev server not running"
> hint page. Forward the port to WSL2 in an elevated PowerShell (get the WSL2
> IP with `wsl hostname -I`; it changes between reboots):
>
> ```powershell
> netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=<WSL2-IP>
> ```
>
> Remove it later with
> `netsh interface portproxy delete v4tov4 listenport=3000 listenaddress=0.0.0.0`.
> Alternatively, WSL2's
> [mirrored networking mode](https://learn.microsoft.com/en-us/windows/wsl/networking#mirrored-mode-networking)
> exposes WSL2 ports on the Windows host directly, no proxy needed.

## Everyday tasks

### Admin site

The admin site is at <http://thunderstore.localhost/djangoadmin/> and requires a
superuser account. `setup_dev_env` already creates one (`admin` / `admin`); use it
to inspect or tweak site and community mappings. To create additional superusers:

```bash
docker compose exec django python manage.py createsuperuser
```

On Windows, prefix interactive commands like this one with `winpty`.

### Test data

`setup_dev_env` seeds test data for you. To re-run only the data population:

```bash
docker compose exec django python manage.py create_test_data
```

### File storage (MinIO)

Local development uses [MinIO](https://github.com/minio/minio) for S3-compatible
file storage, available at <http://thunderstore.localhost:9000/> with
`thunderstore` / `thunderstore` credentials.

### REST API

Swagger documentation is served at `/api/docs/`. The primary endpoint is
`/api/v1/package/`, which lists all active mods; a single mod can be fetched from
`/api/v1/package/{uuid4}/`, where `{uuid4}` is the mod's UUID.

## Testing

```bash
# Run the test suite
docker compose exec django pytest

# Recreate the test database (e.g. after model changes)
docker compose exec django pytest --create-db --migrations
```

CI fails a pull request if it lowers test coverage. To check coverage locally
before submitting:

```bash
docker compose exec django coverage run -m pytest
docker compose exec django coverage report -m
```

### Test duration estimates

CI splits the test run across workers by expected duration, so the duration
database should be refreshed occasionally:

```bash
docker compose exec django pytest --store-durations
```

## Production configuration

The settings below are for **deployments** — local development needs almost none
of them, since the dev defaults live in `docker-compose.yml` and `.env.template`.
See
[`django/thunderstore/core/settings.py`](django/thunderstore/core/settings.py) for
the full set of supported variables.

### General

-   `DEBUG`: Leave unset or `false` in production.
-   `SECRET_KEY`: A long, random, secret string used to hash passwords and other data.
-   `ALLOWED_HOSTS`: Comma-separated hostnames the server answers on, e.g. `beta.thunderstore.io`.
-   `PRIMARY_HOST`: The public name of the server, e.g. `beta.thunderstore.io`.
-   `PROTOCOL`: Protocol used to build URLs — `https://` or `http://`.
-   `REPOSITORY_MAX_PACKAGE_SIZE_MB`: Maximum single package size.
-   `REPOSITORY_MAX_PACKAGE_TOTAL_SIZE_GB`: Maximum total file size used by packages.

### Gunicorn

-   `GUNICORN_WORKER_COUNT`: Number of workers to spawn.
-   `GUNICORN_LOG_LEVEL`: Logging level.

### Django sessions

-   `SESSION_COOKIE_DOMAIN`: If set, shares sessions across a domain and its
    subdomains, e.g. `thunderstore.io`. For local testing use `.thunderstore.localhost`
    (and ensure the `Site` objects point to `thunderstore.localhost`).

### Social auth

-   `SOCIAL_AUTH_SANITIZE_REDIRECTS`: Set `True` to restrict OAuth redirect domains.
-   `SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS`: Allowed OAuth redirect domains, used when
    `SOCIAL_AUTH_SANITIZE_REDIRECTS` is enabled.
-   `SOCIAL_AUTH_INIT_HOST`: Host used for social-auth initialization and callbacks,
    regardless of the host the user is on. Defaults to `AUTH_EXCLUSIVE_HOST`, then to
    the request host.
-   `AUTH_EXCLUSIVE_HOST`: A host used exclusively for auth logic such as the
    social-auth process. If unset, no host is treated as the exclusive auth host.

For local testing:

-   `AUTH_EXCLUSIVE_HOST`: `auth.thunderstore.localhost`
-   `SOCIAL_AUTH_SANITIZE_REDIRECTS`: `True`
-   `SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS`: `auth.thunderstore.localhost,thunderstore.localhost`

#### GitHub OAuth

In GitHub settings (personal or organization), under **Developer Settings → OAuth
Apps**, create a new OAuth application. Set the Authorization callback URL to
`{AUTH_EXCLUSIVE_HOST}/auth/complete/github/` — for example
`http://auth.thunderstore.localhost/auth/complete/github/` locally, or
`https://auth.thunderstore.dev/auth/complete/github/` in production. Then set:

-   `SOCIAL_AUTH_GITHUB_KEY`: The application's `Client ID`.
-   `SOCIAL_AUTH_GITHUB_SECRET`: The application's `Client Secret`.

#### Discord OAuth

In the Discord developer panel, create a new OAuth application and add the callback
URL `{AUTH_EXCLUSIVE_HOST}/auth/complete/discord/` — for example
`http://auth.thunderstore.localhost/auth/complete/discord/` locally, or
`https://auth.thunderstore.dev/auth/complete/discord/` in production. Then set:

-   `SOCIAL_AUTH_DISCORD_KEY`: The application's `Client ID`.
-   `SOCIAL_AUTH_DISCORD_SECRET`: The application's `Client Secret`.

### Storage

The AWS S3 / Boto3 protocol is supported by many vendors, so the exact
implementation varies by provider. See the
[django-storages docs](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html)
and `settings.py` for details. At minimum, set:

-   `AWS_ACCESS_KEY_ID`: Auth key ID.
-   `AWS_SECRET_ACCESS_KEY`: Auth key secret.
-   `AWS_S3_REGION_NAME`: Storage bucket region.
-   `AWS_S3_ENDPOINT_URL`: Storage service endpoint.
-   `AWS_STORAGE_BUCKET_NAME`: Bucket name.
-   `AWS_LOCATION`: Location inside the bucket to upload files to.
-   `AWS_S3_SECURE_URLS`: Set `false` to disable HTTPS (enabled by default).

### Usermedia storage

Usermedia uploads use S3-compatible presigned URLs, so the usermedia backend must
also be S3-compatible:

-   `USERMEDIA_S3_ENDPOINT_URL`: Internally accessible storage endpoint.
-   `USERMEDIA_S3_ACCESS_KEY_ID`: Auth key ID.
-   `USERMEDIA_S3_SECRET_ACCESS_KEY`: Auth key secret.
-   `USERMEDIA_S3_SIGNING_ENDPOINT_URL`: Publicly accessible storage endpoint, used
    when generating presigned URLs (e.g. to bypass the CDN domain).
-   `USERMEDIA_S3_REGION_NAME`: Storage bucket region.
-   `USERMEDIA_S3_STORAGE_BUCKET_NAME`: Storage bucket name.
-   `USERMEDIA_S3_LOCATION`: Location inside the bucket to upload files to.

### Database

Local databases without SSL work out of the box; remote databases over SSL are
also supported.

-   `DATABASE_URL`: The database connection URL.
-   `DB_CLIENT_CERT`: Base64-encoded client certificate (written to `client-cert.pem`).
-   `DB_CLIENT_KEY`: Base64-encoded client key (written to `client-key.pem`).
-   `DB_SERVER_CA`: Base64-encoded server CA (written to `server-ca.pem`).

The default local database from `docker-compose.yml` can be reached from a shell
with `docker compose exec db psql -U django` (password `django`).

### Redis caching

-   `REDIS_URL`: Redis URL used for caching, e.g. `redis://some-host:6379/0`.

## License

Thunderstore is licensed under the terms in [LICENSE](LICENSE).
