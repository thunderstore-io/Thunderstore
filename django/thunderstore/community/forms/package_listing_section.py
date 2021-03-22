from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from ..models import PackageListingSection
from ..models.package_category import PackageCategory


class PackageListingSectionForm(forms.ModelForm):
    class Meta:
        model = PackageListingSection
        exclude = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and hasattr(self.instance, "community"):
            category_qs = PackageCategory.objects.filter(
                community=self.instance.community,
            )
            self.fields["require_categories"].queryset = category_qs
            self.fields["exclude_categories"].queryset = category_qs

    def clean(self):
        community = self.cleaned_data.get(
            "community", getattr(self.instance, "community", None)
        )
        require_categories = self.cleaned_data.get("require_categories", [])
        exclude_categories = self.cleaned_data.get("exclude_categories", [])

        invalid_require_categories = PackageCategory.objects.exclude(
            community=community
        ).filter(Q(pk__in=require_categories) | Q(pk__in=exclude_categories))

        if invalid_require_categories.count() > 0:
            raise ValidationError("All categories must match the selected community")
