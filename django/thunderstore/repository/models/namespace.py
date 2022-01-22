from django.contrib.postgres.fields import CICharField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Manager

from thunderstore.repository.models.package import Package
from thunderstore.repository.validators import PackageReferenceComponentValidator


class Namespace(models.Model):
    objects: "Manager[Namespace]"
    packages: "Manager[Package]"

    name = CICharField(
        primary_key=True,
        max_length=64,
        validators=[PackageReferenceComponentValidator("Namespace name")],
    )
    team = models.ForeignKey(
        "repository.Team",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="namespaces",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "namespace"
        verbose_name_plural = "namespaces"

    def __str__(self):
        return self.name

    def validate(self):
        if self._state.adding:
            for validator in self._meta.get_field("name").validators:
                validator(self.name)
            if Namespace.objects.filter(name__iexact=self.name.lower()).exists():
                raise ValidationError("The namespace name already exists")

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)
