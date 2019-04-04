# Thunderstore

Thunderstore is a mod database and API for downloading Risk of Rain 2 mods.


## Setup guide for development

* Copy `.env.template` to `.env` and modify as you see fit
* Run `docker-compose up`

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
