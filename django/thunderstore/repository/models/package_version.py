import re
import uuid
from typing import TYPE_CHECKING, Iterator, Optional

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import get_storage_class
from django.db import models, transaction
from django.db.models import Manager, Q, QuerySet, Sum, signals
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from thunderstore.core.mixins import AdminLinkMixin
from thunderstore.core.types import UserType
from thunderstore.permissions.mixins import VisibilityMixin, VisibilityQuerySet
from thunderstore.repository.consts import (
    PACKAGE_NAME_REGEX,
    PackageVersionReviewStatus,
)
from thunderstore.repository.models import Package
from thunderstore.repository.package_formats import PackageFormats
from thunderstore.utils.decorators import run_after_commit
from thunderstore.webhooks.audit import (
    AuditAction,
    AuditEvent,
    AuditEventField,
    AuditTarget,
    fire_audit_event,
)
from thunderstore.webhooks.models.release import Webhook

if TYPE_CHECKING:
    from thunderstore.repository.models.package_installer import (
        PackageInstaller,
        PackageInstallerDeclaration,
    )


def get_version_zip_filepath(instance, filename):
    return f"repository/packages/{instance}.zip"


def get_version_png_filepath(instance, filename):
    return f"repository/icons/{instance}.png"


class PackageVersionQuerySet(VisibilityQuerySet):
    def active(self) -> "QuerySet[PackageVersion]":  # TODO: Generic type
        return self.exclude(is_active=False)

    def chunked_enumerate(self, chunk_size=1000) -> Iterator["PackageVersion"]:
        """
        Enumerate over all the results without fetching everything at once.
        Instead, cursor based pagination with deterministic ordering is used
        to fetch each chunk separately, thus saving on memory.

        Server-side cursors would be a better option if the environment allows
        for it, but connection poolers generally make that impossible.

        :param chunk_size: The amount of items fetched at once in each chunk
        :return: Iterator of all the results
        """
        qs = self.order_by("date_created", "id")
        cursor = Q()
        while page := list(qs.filter(cursor)[:chunk_size]):
            cursor = Q(
                date_created__gte=page[-1].date_created,
                id__gt=page[-1].id,
            )
            for entry in page:
                yield entry

    def listed_in(self, community_identifier: str):
        return self.exclude(
            ~Q(package__community_listings__community__identifier=community_identifier),
        )


class PackageVersion(VisibilityMixin, AdminLinkMixin):
    installers: "Manager[PackageInstaller]"
    installer_declarations: "Manager[PackageInstallerDeclaration]"
    objects: "Manager[PackageVersion]" = PackageVersionQuerySet.as_manager()
    id: int

    package = models.ForeignKey(
        "repository.Package",
        related_name="versions",
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="uploaded_versions",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
    )
    downloads = models.PositiveIntegerField(default=0)

    format_spec = models.TextField(
        choices=PackageFormats.choices,
        blank=True,
        null=True,
        help_text="Used to track the latest package format spec this package is compatible with",
    )
    name = models.CharField(
        max_length=Package._meta.get_field("name").max_length,
    )

    # TODO: Split to three fields for each number in the version for better querying performance
    version_number = models.CharField(
        max_length=16,
    )
    website_url = models.CharField(
        max_length=1024,
    )
    description = models.CharField(max_length=256)
    dependencies = models.ManyToManyField(
        "self",
        related_name="dependants",
        symmetrical=False,
        blank=True,
    )
    installers = models.ManyToManyField(
        "repository.PackageInstaller",
        through="repository.PackageInstallerDeclaration",
        related_name="package_versions",
        blank=True,
    )
    readme = models.TextField()
    changelog = models.TextField(blank=True, null=True)

    review_status = models.TextField(
        default=PackageVersionReviewStatus.unreviewed,
        choices=PackageVersionReviewStatus.as_choices(),
    )

    # <packagename>.zip
    file = models.FileField(
        upload_to=get_version_zip_filepath,
        storage=get_storage_class(settings.PACKAGE_FILE_STORAGE)(),
    )
    file_size = models.PositiveBigIntegerField()
    file_tree = models.ForeignKey(
        "storage.DataBlobGroup",
        related_name="package_versions",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    # <packagename>.png
    icon = models.ImageField(
        upload_to=get_version_png_filepath,
    )
    uuid4 = models.UUIDField(default=uuid.uuid4, editable=False)

    def validate(self):
        if not re.match(PACKAGE_NAME_REGEX, self.name):
            raise ValidationError(
                "Package names can only contain a-z A-Z 0-9 _ characters",
            )

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["date_created", "id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("package", "version_number"),
                name="unique_version_per_package",
            ),
            models.CheckConstraint(
                check=PackageFormats.as_query_filter(
                    field_name="format_spec",
                    allow_none=True,
                ),
                name="valid_package_format",
            ),
        ]

    # TODO: Remove in the end of TS-272
    def get_absolute_url(self):
        return reverse(
            "old_urls:packages.version.detail",
            kwargs={
                "owner": self.owner.name,
                "name": self.name,
                "version": self.version_number,
            },
        )

    def get_page_url(self, community_identifier: str) -> str:
        return reverse(
            "communities:community:packages.version.detail",
            kwargs={
                "owner": self.owner.name,
                "name": self.name,
                "version": self.version_number,
                "community_identifier": community_identifier,
            },
        )

    @cached_property
    def is_removed(self):
        if self.package.is_removed:
            return True
        return not self.is_active

    @cached_property
    def display_name(self):
        return self.name.replace("_", " ")

    @cached_property
    def owner(self):
        return self.package.owner

    @cached_property
    def is_deprecated(self):
        return self.package.is_deprecated

    @cached_property
    def is_effectively_active(self):
        return self.is_active and self.package.is_active

    @cached_property
    def full_version_name(self):
        return f"{self.package.full_package_name}-{self.version_number}"

    @cached_property
    def reference(self):
        from thunderstore.repository.package_reference import PackageReference

        return PackageReference(
            namespace=self.owner.name,
            name=self.name,
            version=self.version_number,
        )

    @cached_property
    def _download_url(self):
        return reverse(
            "old_urls:packages.download",
            kwargs={
                "owner": self.package.owner.name,
                "name": self.package.name,
                "version": self.version_number,
            },
        )

    @cached_property
    def full_download_url(self) -> str:
        return f"{settings.PROTOCOL}{settings.PRIMARY_HOST}{self._download_url}"

    @property
    def install_url(self):
        path = f"{self.package.owner.name}/{self.package.name}/{self.version_number}"
        return f"ror2mm://v1/install/{settings.PRIMARY_HOST}/{path}/"

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        if created:
            instance.package.handle_created_version(instance)
            instance.announce_release()
        instance.package.handle_updated_version(instance)

    @staticmethod
    def post_delete(sender, instance, **kwargs):
        instance.package.handle_deleted_version(instance)

    @classmethod
    def get_total_used_disk_space(cls):
        return cls.objects.aggregate(total=Sum("file_size"))["total"] or 0

    @run_after_commit
    def announce_release(self):
        webhooks = Webhook.get_for_package_release(self.package)

        for webhook in webhooks:
            webhook.post_package_version_release(self)

    def _increase_download_counter(self):
        self.downloads += 1
        self.save(update_fields=("downloads",))

    def __str__(self):
        return self.full_version_name

    @staticmethod
    def _get_log_key(version_id: int, client_ip: str) -> str:
        return f"metrics.{client_ip}.download.{version_id}"

    @staticmethod
    def _can_log_download_event(version_id: int, client_ip: Optional[str]) -> bool:
        if not client_ip:
            return False

        if not settings.USE_TIME_SERIES_PACKAGE_DOWNLOAD_METRICS:
            return False

        return cache.set(
            key=PackageVersion._get_log_key(version_id, client_ip),
            value=0,
            timeout=settings.DOWNLOAD_METRICS_TTL_SECONDS,
            nx=True,
        )

    @staticmethod
    def log_download_event(version_id: int, client_ip: Optional[str]):
        from thunderstore.repository.tasks.downloads import log_version_download

        if not PackageVersion._can_log_download_event(version_id, client_ip):
            return

        log_version_download.delay(version_id, timezone.now().isoformat())

    def build_audit_event(
        self,
        *,
        action: AuditAction,
        user_id: Optional[int],
        message: Optional[str] = None,
    ) -> AuditEvent:
        return AuditEvent(
            timestamp=timezone.now(),
            user_id=user_id,
            target=AuditTarget.VERSION,
            action=action,
            message=message,
            related_url=self.package.get_view_on_site_url(),
            fields=[
                AuditEventField(
                    name="Package",
                    value=self.package.full_package_name,
                ),
            ],
        )

    @transaction.atomic
    def reject(
        self,
        agent: Optional[UserType],
        is_system: bool = False,
        message: Optional[str] = None,
    ):
        if is_system or self.can_user_manage_approval_status(agent):
            self.review_status = PackageVersionReviewStatus.rejected
            self.save(update_fields=("review_status",))

            fire_audit_event(
                self.build_audit_event(
                    action=AuditAction.REJECTED,
                    user_id=agent.pk if agent else None,
                    message=message,
                )
            )
        else:
            raise PermissionError()

    @transaction.atomic
    def approve(
        self,
        agent: Optional[UserType],
        is_system: bool = False,
        message: Optional[str] = None,
    ):
        if is_system or self.can_user_manage_approval_status(agent):
            self.review_status = PackageVersionReviewStatus.approved
            self.save(update_fields=("review_status",))

            fire_audit_event(
                self.build_audit_event(
                    action=AuditAction.APPROVED,
                    user_id=agent.pk if agent else None,
                    message=message,
                )
            )
        else:
            raise PermissionError()

    def can_user_manage_approval_status(self, user: Optional[UserType]) -> bool:
        if not user:
            return False

        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        # TODO: Replace this with get_moderated_comunnities or whatever the cached equivalent ends up being
        # from thunderstore.repository.views.package._utils import (
        #     get_moderatable_communities,
        # )
        #
        # moderatable_community_ids = get_moderatable_communities(user)
        #
        # community_ids = [
        #     listing.community.id
        #     for listing in self.community_listings.select_related("community")
        # ]
        #
        # if community_ids and all(
        #     str(cid) in moderatable_community_ids for cid in community_ids
        # ):
        #     return

        return False

    def is_visible_to_user(self, user: Optional[UserType]) -> bool:
        if not self.visibility:
            return False

        if self.visibility.public_detail:
            return True

        if user is None:
            return False

        if self.visibility.owner_detail:
            if self.package.owner.can_user_access(user):
                return True

        if self.visibility.moderator_detail:
            for listing in self.package.community_listings.all():
                if listing.community.can_user_manage_packages(user):
                    return True

        if self.visibility.admin_detail:
            if user.is_superuser:
                return True

        return False

    def set_visibility_from_active_status(self):
        if not self.is_active or not self.package.is_active:
            self.visibility.public_detail = False
            self.visibility.public_list = False
            self.visibility.owner_detail = False
            self.visibility.owner_list = False
            self.visibility.moderator_detail = False
            self.visibility.moderator_list = False

    def set_visibility_from_review_status(self):
        if self.review_status == PackageVersionReviewStatus.rejected:
            self.visibility.public_detail = False
            self.visibility.public_list = False

    @transaction.atomic
    def update_visibility(self):
        return
        # TODO: Re-enable once visibility system fixed
        # original = self.visibility.as_tuple()
        #
        # self.set_default_visibility()
        #
        # self.set_visibility_from_active_status()
        #
        # self.set_visibility_from_review_status()
        #
        # if self.visibility.as_tuple() != original:
        #     self.visibility.save()
        #     self.package.update_visibility()  # package's visibility may change because of its versions


signals.post_save.connect(PackageVersion.post_save, sender=PackageVersion)
signals.post_delete.connect(PackageVersion.post_delete, sender=PackageVersion)
