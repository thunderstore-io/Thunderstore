from typing import List

from django import forms
from django.core.exceptions import ValidationError

from thunderstore.community.models import PackageCategory
from thunderstore.webhooks.models.release import Webhook


class WebhookForm(forms.ModelForm):
    class Meta:
        model = Webhook
        exclude = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            category_qs = PackageCategory.objects.filter(
                community=self.instance.community,
            )
            self.fields["exclude_categories"].queryset = category_qs
            self.fields["require_categories"].queryset = category_qs

    def clean(self):
        community = self.cleaned_data.get(
            "community", getattr(self.instance, "community", None)
        )

        def validate_cats(cats: List[str]):
            invalid_categories = PackageCategory.objects.exclude(
                community=community
            ).filter(pk__in=cats)
            if invalid_categories.count() > 0:
                raise ValidationError(
                    "All categories must match the community of the Webhook"
                )

        validate_cats(self.cleaned_data.get("exclude_categories", []))
        validate_cats(self.cleaned_data.get("require_categories", []))


class WebhookAdminForm(WebhookForm):
    """
    Same as WebhookForm but without allowing any category selection before first
    save, as the admin view will populate the category selection with all
    categories in the DB otherwise.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["exclude_categories"].queryset = PackageCategory.objects.none()
            self.fields["require_categories"].queryset = PackageCategory.objects.none()
