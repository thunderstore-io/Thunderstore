from typing import Optional

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from thunderstore.community.models.package_category import PackageCategory
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.core.types import UserType

User = get_user_model()


class PackageListingEditCategoriesForm(forms.ModelForm):
    instance: PackageListing
    categories = forms.ModelMultipleChoiceField(
        queryset=None, show_hidden_initial=True, required=False
    )

    class Meta:
        model = PackageListing
        fields = ["categories"]

    def __init__(self, user: Optional[UserType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["categories"].queryset = PackageCategory.objects.filter(
            community__identifier=self.instance.community.identifier
        )

    def clean(self):
        self.instance.ensure_update_categories_permission(self.user)
        if (
            len(
                set(self.instance.categories.all()).symmetric_difference(
                    self.initial["categories"]
                )
            )
            != 0
        ):
            raise ValidationError(
                "Listings current categories do not match provided ones"
            )
        else:
            return super().clean()
