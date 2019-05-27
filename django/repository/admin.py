from django.contrib import admin


from repository.models import Package
from repository.models import PackageVersion
from repository.models import UploaderIdentity
from repository.models import UploaderIdentityMember


class UploaderIdentityMemberAdmin(admin.StackedInline):
    model = UploaderIdentityMember
    extra = 0
    list_display = (
        "user",
        "identity",
        "role",
    )


@admin.register(UploaderIdentity)
class UploaderIdentityAdmin(admin.ModelAdmin):
    inlines = [
        UploaderIdentityMemberAdmin,
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        else:
            return []

    readonly_fields = (
        "name",
    )
    list_display = (
        "name",
    )


class PackageVersionInline(admin.StackedInline):
    model = PackageVersion
    readonly_fields = (
        "date_created",
        "dependencies",  # TODO: Add some way to manage dependencies that doesn't suck
        # "description",  # TODO: Add to package, and make that modifiable
        "downloads",
        "file",
        "icon",
        "name",
        # "readme",  # TODO: Add to package, and make that modifiable
        "version_number",
        "website_url",
        "website_url",
    )
    extra = 0
    filter_horizontal = ("dependencies",)


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    inlines = [
        PackageVersionInline,
    ]

    readonly_fields = (
        "date_created",
        "downloads",
        "name",
        "owner",
    )
    list_display = (
        "name",
        "owner",
        "is_active",
        "is_deprecated",
        "is_pinned",
    )
    list_filter = (
        "is_active",
        "is_pinned",
        "is_deprecated",
    )
