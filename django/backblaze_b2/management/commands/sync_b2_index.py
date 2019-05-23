from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from storages.utils import setting

from ...api import BackblazeB2API
from ...models import BackblazeB2File


class Command(BaseCommand):
    help = "Fetches a list of all files in the configured b2 storage"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        key_id = setting("B2_KEY_ID")
        key = setting("B2_KEY")
        bucket_id = setting("B2_BUCKET_ID")
        location = setting("B2_LOCATION")

        if not key and key_id and bucket_id:
            raise CommandError("No b2 storage is currently configured")

        self.api = BackblazeB2API(
            application_key_id=key_id, application_key=key, bucket_id=bucket_id
        )
        self.sync_b2_index(location=location)

    def sync_b2_index(self, location="", next_name=""):
        files = self.api.list_file_names(prefix=location, start_file_name=next_name)
        next_name = files.get("nextFileName", None)

        for file in files["files"]:
            file_obj = BackblazeB2File.objects.filter(name=file["fileName"]).first()
            if not file_obj:
                file_obj = BackblazeB2File(name=file["fileName"])

            file_obj.b2_id = file["fileId"]
            file_obj.bucket_id = file["bucketId"]
            file_obj.content_length = file["contentLength"]
            file_obj.content_sha1 = file["contentSha1"]
            file_obj.content_type = file["contentType"]
            file_obj.save()
            print(f"Synced file {file_obj.name}")

        if next_name:
            self.sync_b2_index(location=location, next_name=next_name)
