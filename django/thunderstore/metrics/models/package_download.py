from django.db import models


class PackageVersionDownloadEvent(models.Model):
    id = models.BigAutoField(primary_key=True, editable=False)
    version_id = models.BigIntegerField(db_index=True)
    timestamp = models.DateTimeField()
