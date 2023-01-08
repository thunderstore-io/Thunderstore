from celery import shared_task

from thunderstore.schema_import.sync import sync_thunderstore_schema


@shared_task
def sync_ecosystem_schema():
    sync_thunderstore_schema()
