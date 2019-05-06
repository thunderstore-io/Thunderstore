from io import BytesIO

from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.core.exceptions import SuspiciousOperation

from storages.utils import (
    clean_name, get_available_overwrite_name, safe_join, setting
)

from .models import BackblazeB2File
from .api import BackblazeB2API


@deconstructible
class BackblazeB2Storage(Storage):
    application_key_id = setting("B2_KEY_ID")
    application_key = setting("B2_KEY")
    bucket_id = setting("B2_BUCKET_ID")
    location = setting("B2_LOCATION")
    file_overwrite = setting("B2_FILE_OVERWRITE", True)

    def __init__(self, **settings):
        # Override class parameters from kwargs
        for name, value in settings.items():
            if hasattr(self, name):
                setattr(self, name, value)

        self.b2api = BackblazeB2API(
            application_key_id=self.application_key_id,
            application_key=self.application_key,
            bucket_id=self.bucket_id,
        )
        self.cache = {}

    def _open(self, name, mode="rb"):
        name = self._normalize_name(clean_name(name))
        # TODO: Use streaming
        content = self.b2api.download_file(self.self.get_b2_id(name))
        content_buffer = BytesIO()
        content_buffer.write(content)
        content_buffer.seek(0)
        return File(content_buffer, name)

    def _save(self, name, content):
        cleaned_name = clean_name(name)
        name = self._normalize_name(cleaned_name)
        response = self.b2api.upload_file(name, content)
        data = response.json()
        assert data["fileName"] == name
        file_obj = BackblazeB2File.objects.filter(
            name=name
        ).first()
        if not file_obj:
            file_obj = BackblazeB2File(name=name)

        file_obj.b2_id = data["fileId"]
        file_obj.bucket_id = data["bucketId"]
        file_obj.content_length = data["contentLength"]
        file_obj.content_sha1 = data["contentSha1"]
        file_obj.content_type = data["contentType"]
        file_obj.save()
        self.cache[name] = file_obj
        return cleaned_name

    def get_b2_id(self, name):
        if name in self.cache:
            return self.cache[name]
        return (
            BackblazeB2File.objects
            .values_list("b2_id", flat=True)
            .get(name=name)
        )

    def _normalize_name(self, name):
        """
        Normalizes the name so that paths like /path/to/ignored/../something.txt
        and ./file.txt work.  Note that clean_name adds ./ to some paths so
        they need to be fixed here. We check to make sure that the path pointed
        to is not outside the directory specified by the LOCATION setting.
        """
        try:
            return safe_join(self.location, name)
        except ValueError:
            raise SuspiciousOperation(f"Attempted access to '{name}' denied.")

    def delete(self, name):
        name = self._normalize_name(clean_name(name))
        raise NotImplementedError()  # TODO: Implement

    def exists(self, name):
        name = self._normalize_name(clean_name(name))
        return (
            BackblazeB2File.objects
            .filter(name=name)
            .exists()
        )

    def listdir(self, name):
        name = self._normalize_name(clean_name(name))
        raise NotImplementedError()  # TODO: Implement

    def size(self, name):
        name = self._normalize_name(clean_name(name))
        return (
            BackblazeB2File.objects
            .values_list("content_length", flat=True)
            .get(name=name)
        )

    def modified_time(self, name):
        name = self._normalize_name(clean_name(name))
        return timezone.make_naive(
            BackblazeB2File.objects
            .values_list("modified_time", flat=True)
            .get(name=name)
        )

    def get_modified_time(self, name):
        name = self._normalize_name(clean_name(name))
        modified = (
            BackblazeB2File.objects
            .values_list("created_time", flat=True)
            .get(name=name)
        )
        return modified if setting("USE_TZ") else timezone.make_naive(modified)

    def get_created_time(self, name):
        name = self._normalize_name(clean_name(name))
        created = (
            BackblazeB2File.objects
            .values_list("created_time", flat=True)
            .get(name=name)
        )
        return created if setting("USE_TZ") else timezone.make_naive(created)

    def url(self, name):
        name = self._normalize_name(clean_name(name))
        return self.b2api.get_file_url(name)

    def get_available_name(self, name, max_length=None):
        name = get_available_overwrite_name(clean_name(name), max_length)
        if self.exists(name) and not self.file_overwrite:
            raise ValueError("File with the same name already exists")
        return super(BackblazeB2Storage, self).get_available_name(name, max_length)
