from django.db import models


class BackblazeB2File(models.Model):
    b2_id = models.CharField(
        max_length=2048,
        unique=True,
        db_index=True,
    )
    name = models.CharField(
        max_length=2048,
        unique=True,
        db_index=True,
    )
    bucket_id = models.CharField(max_length=2048)
    content_length = models.BigIntegerField()
    content_sha1 = models.CharField(max_length=2048)
    content_type = models.CharField(max_length=2048)
    created_time = models.DateTimeField(auto_now_add=True)
    modified_time = models.DateTimeField(auto_now=True)
