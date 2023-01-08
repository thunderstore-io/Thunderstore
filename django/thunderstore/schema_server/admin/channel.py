from django.contrib import admin

from thunderstore.schema_server.models import SchemaChannel


class SchemaChannelAuthorizedUserInline(admin.TabularInline):
    model = SchemaChannel.authorized_users.through
    raw_id_fields = ("user",)
    extra = 0


@admin.register(SchemaChannel)
class SchemaChannelAdmin(admin.ModelAdmin):
    inlines = [
        SchemaChannelAuthorizedUserInline,
    ]

    exclude = ("authorized_users",)
    readonly_fields = (
        "latest",
        "identifier",
        "datetime_created",
        "datetime_updated",
    )
    list_display = ("identifier",)
    search_fields = ("identifier",)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return [x for x in self.readonly_fields if x != "identifier"]
