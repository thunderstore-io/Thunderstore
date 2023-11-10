# Upgrading the development environment DB

## Start fresh

If the DB docker image major version is bumped, it will break the local database
as postgres won't implicitly upgrade old data.

In order to get the DB working again, you'll simply need to delete the volume
as follows:

```bash
docker compose down # This is required as volumes in use can't be deleted
docker volume rm thunderstore_db-data
```

After the above, the db service should run normally

## Keep old data

Make sure to checkout a git commit that still uses a DB version which works in
your devenv before proceeding.

### 1. Set up a mount point for the db in `docker-compose.yml`

This example adds the `./db-mount` directory:

```diff
services:
  db:
    image: postgres:13.12-alpine
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - db-data:/var/lib/postgresql/data
+     - "./db-mount:/db-mount"
```

### 2. Dump your database

Start the docker compose stack and open a shell in the db container with
`docker compose exec db bash`. Then run the following:

```bash
PGPASSWORD=django pg_dump -U django django > /db-mount/django.sql
```

Make sure to use the mount point created in step 1

### 3. Update the db container to a fresh state

-   Take down the stack (`docker compose down`, yes you need `down` and not just stop)
-   Checkout to a git commit with the new db version
    -   Make sure to re-apply the volume mount from step 1 if it gets overwritten.
-   Run `docker volume rm thunderstore_db-data`
-   Start the stack (`docker compose up`)

### 4. Load the dump

Same as before, get a shell with `docker compose exec db bash` and run the
following:

```bash
PGPASSWORD=django psql -U django django < /db-mount/django.sql
```

### 5. Cleanup

Remove the changes from step 1 and delete the `db-mount` directory that was
created in the project.
