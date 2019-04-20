# Thunderstore

Thunderstore is a mod database and API for downloading Risk of Rain 2 mods.


## Setup guide for development

* Copy `.env.template` to `.env` and modify as you see fit
* Run `docker-compose up`
* Run `docker-compose exec django python manage.py migrate` in another terminal

## Mod package format

Mod packages are `.zip` files, with at least the following contents:

* `/icon.png` - A PNG icon for the mod, must be 256x256 resolution.
* `/README.md` - A readme file to be rendered on the mod's page.
* `/manifest.json` - A `.json` file with the mod's metadata. Required filds are:
    * `name` - Name of the mod. Allowed characters: `a-z A-Z 0-9 _`. No spaces.
    * `description` - A short description of the mod, shown on the mod list. Max
    250 characters
    * `website_url` - URL of the mod's website (e.g. GitHub repo). Can be empty,
    but the key must still exists (use an empty string for example).
    * `version_number` - Version number of the mod, following the semantic version
    format `Major.Minor.Patch`. For example: `1.3.2`.

Example `manifest.json` contents:
```json
{
    "name": "TestMod",
    "version_number": "1.1.0",
    "website_url": "https://github.com/risk-of-thunder",
    "description": "This is a description for a mod. Max length is 250 characters"
}
```

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

- `DEBUG`: Should be either set to false or not at all for production
- `SECRET_KEY`: A long and random string, used to hash passwords and other data.
Should remain secret, as is implied by the name.
- `ALLOWED_HOSTS`: Comma separated list of hostnames this server can be
connected with. For example `thunderstore.mythic.dev`
- `SERVER_NAME`: The public name of the server, such as
`thunderstore.mythic.dev`
- `PROTOCOL`: The protocol which to use to build URLs to the server. Either
`https://` or `http://`.

### GitHub OAuth

To set up GitHub OAuth, head to settings on GitHub (either personal or
organization settings), and from under `Developer Settings` select `OAuth Apps`.

Create a new OAuth Application, and use `{server}/auth/complete/github/` as the
Authorization callback URL, where `{server}` is replaced with the protocol and
server name that is accessible. For example for local you could use
`http://localhost/auth/complete/github/`, whereas for a live environment
`https://thunderstore.mythic.dev/auth/complete/github/`

After creating the OAuth application, you must also provide the following
environment variables to the application:

- `SOCIAL_AUTH_GITHUB_KEY`: The `Client ID` value of the OAuth application
- `SOCIAL_AUTH_GITHUB_SECRET` The `Client Secret` value of the OAuth application

### Google Analytics

You can enable google analytics by supplying a google analytics tracking ID via
environment variables.

- `GOOGLE_ANALYTICS_ID`: The Google Analytics Tracking ID of your account


### Google Cloud Media Storage

You need to set up a google cloud storage bucket and create a service account
that has access to the storage bucket.

Set the following variables:

- `GS_BUCKET_NAME`: The name/id of the storage bucket
- `GS_PROJECT_ID`: The ID of the project the bucket resides in
- `GS_LOCATION`: The subfolder under which the files should be stored in the
bucket. Can be left empty or undefined.
- `GS_CREDENTIALS`: Base64 encoded (with no newlines) string of the service
account credentials json file, that can be downloaded from google cloud console.

### Database

Database configuration is pretty straight forward if using a local database
where no SSL is required, but remote database via SSL connections is also
supported.

- `DATABASE_URL`: The database URL to use for a database connection
- `DB_CLIENT_CERT`: Base64 encoded client certificate to use for the database
connection. Will be placed to `client-cert.pem`
- `DB_CLIENT_KEY`: Base64 encoded client key to use for the database connection.
Will be placed to `client-key.pem`
- `DB_SERVER_CA`: Base64 encoded server CA to use for the database connection.
Will be placed to `server-ca.pem`
