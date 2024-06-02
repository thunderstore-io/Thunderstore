from django.contrib import admin
from django.db.models import BooleanField, ExpressionWrapper, Q, QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.safestring import mark_safe

from thunderstore.community.models import PackageListing
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.tasks.files import extract_package_version_file_tree


def extract_file_list(modeladmin, request, queryset: QuerySet):
    for entry in queryset:
        extract_package_version_file_tree.delay(entry.pk)


extract_file_list.short_description = "Queue file list extraction"


@admin.register(PackageVersion)
class PackageVersionAdmin(admin.ModelAdmin):
    model = PackageVersion
    actions = [
        extract_file_list,
    ]
    list_select_related = (
        "package",
        "package__owner",
        "package__namespace",
    )
    list_filter = ("is_active", "date_created")
    list_display = (
        "package",
        "version_number",
        "is_active",
        "file_size",
        "downloads",
        "date_created",
        "has_file_tree",
    )
    search_fields = (
        "package__owner__name",
        "package__namespace__name",
        "version_number",
        "file_tree__entries__blob__checksum_sha256",
    )
    date_hierarchy = "date_created"
    readonly_fields = (
        "file_tree_link",
        "listings",
    )
    exclude = (
        "website_url",
        "file_tree",
        "readme",
        "changelog",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .annotate(
                has_file_tree=ExpressionWrapper(
                    ~Q(file_tree=None), output_field=BooleanField()
                )
            )
        )

    def has_file_tree(self, obj):
        return obj.has_file_tree

    has_file_tree.boolean = True
    has_file_tree.admin_order_field = "has_file_tree"

    def file_tree_link(self, obj):
        if not obj.file_tree:
            return None
        url = reverse(
            f"admin:{obj.file_tree._meta.app_label}_{obj.file_tree._meta.model_name}_change",
            kwargs={"object_id": obj.file_tree.pk},
        )
        return mark_safe(f'<a href="{url}">{obj.file_tree}</a>')

    file_tree_link.short_description = "File tree"

    def listings(self, obj):
        listings = PackageListing.objects.filter(package__versions=obj)
        links = ""
        for listing in listings:
            links += f'<a href="{listing.get_admin_url()}">{listing.community}</a><br/>'
        return mark_safe(links)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
