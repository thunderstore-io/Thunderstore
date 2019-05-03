from django.contrib import admin


from backblaze_b2.models import BackblazeB2File


@admin.register(BackblazeB2File)
class BackblazeB2FileAdmin(admin.ModelAdmin):
    readonly_fields = (
        "b2_id",
        "name",
        "bucket_id",
        "content_length",
        "content_sha1",
        "content_type",
        "created_time",
        "modified_time",
    )
    list_display = (
        "name",
        "created_time",
        "modified_time",
    )
    list_filter = (
        "bucket_id",
    )
