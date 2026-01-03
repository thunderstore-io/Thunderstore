from django.contrib.postgres.indexes import BrinIndex
from django.db import models


class PackageVersionDownloadEvent(models.Model):
    id = models.BigAutoField(primary_key=True, editable=False)
    version_id = models.BigIntegerField(db_index=True)
    timestamp = models.DateTimeField()
    
    class Meta:
        indexes = [
            # A BRIN index is perfect here - it is 100x-1000x smaller than a b-tree and much faster
            # to create and insert. This table is ~20M rows right now, so saves a lot of space.
            # This table is insert-only, and filtering happens by timestamp ranges.
            BrinIndex(fields=["timestamp"]),
        ]
