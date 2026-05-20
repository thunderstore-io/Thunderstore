from django.db import models
from django.db.models import Manager

from thunderstore.core.mixins import TimestampMixin


class ReleaseGroup(TimestampMixin, models.Model):
    objects: "Manager[ReleaseGroup]"
    community = models.ForeignKey("community.Community", on_delete=models.CASCADE)
    slug = models.CharField(max_length=64)
    display_name = models.CharField(max_length=256)
    release_name = models.CharField(max_length=256, blank=True, null=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        if self.release_name:
            return f"{self.community.name} -> {self.display_name} ({self.release_name})"
        else:
            return f"{self.community.name} -> {self.display_name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("slug", "community"),
                name="unique_release_group_per_community",
            ),
        ]
        verbose_name = "release group"
        verbose_name_plural = "release groups"


class GameVersion(TimestampMixin, models.Model):
    objects: "Manager[GameVersion]"
    community = models.ForeignKey("community.Community", on_delete=models.CASCADE)
    release_group = models.ForeignKey("ReleaseGroup", on_delete=models.CASCADE)
    version = models.CharField(max_length=64)
    release_name = models.CharField(max_length=256, blank=True, null=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.release_name:
            return f"{self.community.name} -> {self.version} ({self.release_name})"
        else:
            return f"{self.community.name} -> {self.version}"

    @property
    def display_name(self) -> str:
        if self.release_name:
            return f"{self.version} - {self.release_name}"
        return self.version

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("version", "community"),
                name="unique_game_version_per_community",
            ),
        ]
        verbose_name = "game version"
        verbose_name_plural = "game versions"
