from django.db import models


class DynamicHTML(models.Model):
    name = models.CharField(max_length=256)
    head_content = models.TextField(null=True, blank=True)
    body_content = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(
        default=True,
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
    )
    date_modified = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Dynamic HTML"
        verbose_name_plural = "Dynamic HTML"
