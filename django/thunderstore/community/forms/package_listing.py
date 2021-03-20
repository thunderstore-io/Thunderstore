from django import forms
from django.core.exceptions import ValidationError

from ..models import PackageListing
from ..models.package_category import PackageCategory


class PackageListingForm(forms.ModelForm):
    class Meta:
        model = PackageListing
        exclude = ["comments_thread"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and hasattr(self.instance, "community"):
            self.fields["categories"].queryset = PackageCategory.objects.filter(
                community=self.instance.community,
            )

    def clean(self):
        categories = self.cleaned_data.get("categories", [])
        community = self.cleaned_data.get(
            "community", getattr(self.instance, "community", None)
        )
        invalid_categories = PackageCategory.objects.exclude(
            community=community
        ).filter(pk__in=categories)
        if invalid_categories.count() > 0:
            raise ValidationError(
                "All PackageListing categories must match the community of the PackageListing"
            )
