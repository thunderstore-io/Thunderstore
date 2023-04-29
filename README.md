# Thunderstore

[![codecov](https://codecov.io/gh/thunderstore-io/Thunderstore/branch/master/graph/badge.svg)](https://codecov.io/gh/thunderstore-io/Thunderstore)

Thunderstore is a mod database and API for downloading mods.

## Setup guide for development

##### If you need a more basic setup for frontend development, see the [basic setup docs](docs/run_basic.md).

-   Copy `.env.template` to `.env` and modify as you see fit
-   Run `docker-compose up`
-   Run `docker-compose exec django python manage.py migrate` in another terminal
-   Run `docker-compose exec django python manage.py shell` and enter the
    following code:

```python
from django.contrib.sites.models import Site
Site.objects.create(domain="thunderstore.localhost", name="Thunderstore")
```

**Make sure to substitute `localhost` with what you use to connect to the site!**
In general, you should use `thunderstore.localhost` as the main domain to handle
auth-scoping correctly (see `SESSION_COOKIE_DOMAIN` later on)

You will also need to navigate to the admin panel (`/djangoadmin`)
and configure a mapping from a site to a community. You can create a superuser
account with the `createsuperuser` Django management command (akin to how
migrate was run) to gain access to the admin panel.

To connect a site to a community, you will need to:

1. Make sure at least one Community object exists or create one
   (`Risk of Rain 2` should be created automatically)
2. Make sure at least one Site object exists or create one
3. Make the site object's `domain name` attribute match what you use for
   connecting to your development environment
4. Create a new Community Site object, linking the two together

### Test data population

There's a script for populating the local database with test data. You can run
it as follows:

```bash
docker-compose exec django python manage.py create_test_data
```

## Minio

In local development, [minio](https://github.com/minio/minio) is used for S3
compatible file storage. You can access it via http://localhost:9000/ with
`thunderstore:thunderstore` credentials

## REST API docs

The REST API swagger documentation can be viewed from `/api/docs/`.

At the current moment, the only relevant API is `/api/v1/package/`, which lists
all the active mods in the database. A specific mod can also be fetched if
necessary with the `/api/v1/package/{uuid4}/` endpoint, where `{uuid4}` is
replaced with the mod's uuid4 value.

## Admin site

The admin site can be accessed from `/djangoadmin/`. To view the admin site, you
need an admin account.

Assuming docker is being used, the admin account can be created as follows:

```
docker-compose exec django python manage.py createsuperuser
```

Do note that if you're running on Windows, you will need to use winpty for
running that command.

## Environment variable configuration for production

### General variables

-   `DEBUG`: Should be either set to false or not at all for production
-   `SECRET_KEY`: A long and random string, used to hash passwords and other data.
    Should remain secret, as is implied by the name.
-   `ALLOWED_HOSTS`: Comma separated list of hostnames this server can be
    connected with. For example `beta.thunderstore.io`
-   `PRIMARY_HOST`: The public name of the server, such as
    `beta.thunderstore.io`
-   `PROTOCOL`: The protocol which to use to build URLs to the server. Either
    `https://` or `http://`.
-   `REPOSITORY_MAX_PACKAGE_SIZE_MB`: The maximum single package size
-   `REPOSITORY_MAX_PACKAGE_TOTAL_SIZE_GB`: The maximum total file size used by packages

### Gunicorn

-   `GUNICORN_WORKER_COUNT`: Used to control how many workers gunicorn will spawn
-   `GUNICORN_LOG_LEVEL`: Used to control gunicorn's logging level

### Django

-   `SESSION_COOKIE_DOMAIN`: If set, allows sessions to be shared within a domain
    and its subdomains. For example: `thunderstore.io`

For local testing, recommended values are:

-   `SESSION_COOKIE_DOMAIN`: `thunderstore.localhost`

Make sure also to have the Site objects point to `thunderstore.localhost` or some
of its subdomains, such as `test.thunderstore.localhost`.

### Social Auth

-   `SOCIAL_AUTH_SANITIZE_REDIRECTS`: Set to `True` if you want to restrict OAuth redirect domains.
-   `SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS`: List allowed OAuth redirect domains, used if
    `SOCIAL_AUTH_SANITIZE_REDIRECTS` is enabled.
-   `SOCIAL_AUTH_INIT_HOST`: The host used for social auth initializations and callbacks,
    regardless of which host the user is currently on. If not set, defaults to the same
    value as `AUTH_EXCLUSIVE_HOST`. If neither are set, defaults to the host
    of the request.
-   `AUTH_EXCLUSIVE_HOST`: A hostname/domain which will exclusively be used for
    auth related logic, such as the social auth process. If not set, no host
    is treated as the exclusive auth host.

For local testing, recommended values are:

-   `AUTH_EXCLUSIVE_HOST`: `auth.thunderstore.localhost`
-   `SOCIAL_AUTH_SANITIZE_REDIRECTS`: `auth.thunderstore.localhost,thunderstore.localhost`

### GitHub OAuth

To set up GitHub OAuth, head to settings on GitHub (either personal or
organization settings), and from under `Developer Settings` select `OAuth Apps`.

Create a new OAuth Application, and use
`{AUTH_EXCLUSIVE_HOST}/auth/complete/github/` as the Authorization callback
URL, where `{AUTH_EXCLUSIVE_HOST}` is replaced with the value that was used for
the `AUTH_EXCLUSIVE_HOST` setting. For example for local you could use
`http://auth.localhost/auth/complete/github/`, whereas for a live environment
`https://auth.thunderstore.dev/auth/complete/github/`

After creating the OAuth application, you must also provide the following
environment variables to the application:

-   `SOCIAL_AUTH_GITHUB_KEY`: The `Client ID` value of the OAuth application
-   `SOCIAL_AUTH_GITHUB_SECRET` The `Client Secret` value of the OAuth application

### Discord OAuth

To set up a Discord OAuth, head to the Discord developer panel, and create a new
OAuth application. Add a callback URL to
`{AUTH_EXCLUSIVE_HOST}/auth/complete/discord/`, where `{AUTH_EXCLUSIVE_HOST}`
is replaced with the value that was used for the `AUTH_EXCLUSIVE_HOST` setting.
For example for local you could use
`http://auth.localhost/auth/complete/discord/`, whereas for a live environment
`https://auth.thunderstore.dev/auth/complete/discord/`

-   `SOCIAL_AUTH_DISCORD_KEY`: The `Client ID` value of the OAuth application
-   `SOCIAL_AUTH_DISCORD_SECRET` The `Client Secret` value of the OAuth
    application

### Storage

The AWS S3 / Boto3 protocol is supported by multiple vendors and services, and
such the implementation may vary depending on the provider.

Refer to
https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html for
more details on the implementation. Also see
[thunderstore/core/settings.py](django/thunderstore/core/settings.py) for what environment variables are
currently implemented.

At the very least set the following variables:

-   `AWS_ACCESS_KEY_ID`: Auth key ID
-   `AWS_SECRET_ACCESS_KEY`: Auth key secret
-   `AWS_S3_REGION_NAME`: Storage bucket region
-   `AWS_S3_ENDPOINT_URL`: Storage service endpoint
-   `AWS_STORAGE_BUCKET_NAME`: Bucket name
-   `AWS_LOCATION`: Location inside the bucket where to upload files
-   `AWS_S3_SECURE_URLS`: Set to false to disable HTTPS, enabled by default

### Usermedia storage

The usermedia APIs work by leveraging S3-compatible storage presigned URLs to
handle the actual upload. As such, the usermedia backend must also be a S3
compatible storage backend. Likewise, the usermedia storage backend can be
configured with environment variables:

-   `USERMEDIA_S3_ENDPOINT_URL`: Internally accessible storage service endpoint
-   `USERMEDIA_S3_ACCESS_KEY_ID`: Auth key ID
-   `USERMEDIA_S3_SECRET_ACCESS_KEY`: Auth key secret
-   `USERMEDIA_S3_SIGNING_ENDPOINT_URL`: Publicly accessible storage service endpoint
-   `USERMEDIA_S3_REGION_NAME`: Storage bucket region
-   `USERMEDIA_S3_STORAGE_BUCKET_NAME`: Storage bucket name
-   `USERMEDIA_S3_LOCATION`: Location inside the bucket where to upload files

The largest difference compared to the AWS S3 configuration is the addition of
a `USERMEDIA_S3_SIGNING_ENDPOINT_URL`. If provided, this will be used when
generating pre-signed URLs. Can be used to bypass the CDN domain for example.

### Database

Database configuration is pretty straight forward if using a local database
where no SSL is required, but remote database via SSL connections is also
supported.

-   `DATABASE_URL`: The database URL to use for a database connection
-   `DB_CLIENT_CERT`: Base64 encoded client certificate to use for the database
    connection. Will be placed to `client-cert.pem`
-   `DB_CLIENT_KEY`: Base64 encoded client key to use for the database connection.
    Will be placed to `client-key.pem`
-   `DB_SERVER_CA`: Base64 encoded server CA to use for the database connection.
    Will be placed to `server-ca.pem`

The default local database configured in `docker-compose.yml` can be accessed:

-   From shell: `docker-compose exec db psql -U django`
-   From browser: navigate to `localhost:8080/?pgsql=db&username=django`
    and use password `django`

### Redis caching

You can enable caching to the redis backend by supplying a redis URL

-   `REDIS_URL`: The redis database URL to use for caching, e.g.
    `redis://some-host:6379/0`

## Testing

Tests can be run with this command: `docker-compose exec django pytest`
If you need to recreate to database,
use the following: `docker-compose exec django pytest --create-db --migrations`

The CI pipeline checks that new PRs don't lower the test coverage. Since this
process is rather slow, you might want to check the coverage locally before
submitting a PR.

-   To update coverage file, run `docker-compose exec django coverage run -m pytest`
-   To see the coverage report, run `docker-compose exec django coverage report -m`

### Test duration estimates

The test run is split across multiple workers on the CI pipeline, and the split
aims to balance test across all the available workers in equal amounts of time
consumption.

To be able to do so accurately, the test duration database has to be up to date.
As such it's a good idea to update the test duration database every now and
then.

The test duration database can be updated by running the full test suite with
the `--store-durations` flag. So a full command example would be

```bash
docker-compose exec django pytest --store-durations
```
