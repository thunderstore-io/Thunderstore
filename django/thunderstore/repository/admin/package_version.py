from django.contrib import admin
from django.db import transaction
from django.db.models import BooleanField, ExpressionWrapper, Q, QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.safestring import mark_safe

from thunderstore.community.models import PackageListing
from thunderstore.repository.consts import PackageVersionReviewStatus
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.tasks.files import extract_package_version_file_tree


def extract_file_list(modeladmin, request, queryset: QuerySet):
    for entry in queryset:
        extract_package_version_file_tree.delay(entry.pk)


extract_file_list.short_description = "Queue file list extraction"


@transaction.atomic
def reject_version(modeladmin, request, queryset: QuerySet[PackageVersion]):
    for version in queryset:
        version.reject(
            agent=request.user, rejection_reason="Invalid submission", is_system=False
        )


reject_version.short_description = "Reject"


@transaction.atomic
def approve_version(modeladmin, request, queryset: QuerySet[PackageVersion]):
    for version in queryset:
        version.approve(agent=request.user, is_system=False)


approve_version.short_description = "Approve"


@admin.register(PackageVersion)
class PackageVersionAdmin(admin.ModelAdmin):
    model = PackageVersion
    actions = [
        extract_file_list,
        reject_version,
        approve_version,
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
        "review_status",
        "file_size",
        "downloads",
        "date_created",
        "has_file_tree",
    )
    search_fields = (
        "package__owner__name",
        "package__namespace__name",
        "version_number",
    )
    date_hierarchy = "date_created"
    readonly_fields = [x.name for x in PackageVersion._meta.fields] + [
        "file_tree_link",
        "listings",
    ]
    exclude = [
        "file_tree",
    ]

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

    def get_readonly_fields(self, request, obj=None):
        return [x for x in self.readonly_fields if x not in self.exclude]

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
        url = reverse(
            f"admin:{PackageListing._meta.app_label}_{PackageListing._meta.model_name}_changelist",
        )
        return mark_safe(
            f'<a href="{url}?package__exact={obj.package.pk}">View package listings</a>'
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
