from typing import Optional

from django import forms
from django.contrib.auth import get_user_model

from thunderstore.core.types import UserType
from thunderstore.repository.models import Package, PackageRating
from thunderstore.repository.permissions import ensure_can_rate_package

User = get_user_model()


class RateForm(forms.Form):
    def __init__(self, user: Optional[UserType], package: Package, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.package = package

    def clean(self):
        ensure_can_rate_package(self.user, self.package)
        target_state = self.data.get("target_state", None)
        if target_state == "rated":
            self.cleaned_data["target_state"] = "rated"
        elif target_state == "unrated":
            self.cleaned_data["target_state"] = "unrated"
        else:
            raise forms.ValidationError("Given target_state is invalid")

        return super().clean()

    def execute(self):
        if self.cleaned_data["target_state"] == "rated":
            PackageRating.objects.get_or_create(rater=self.user, package=self.package)
            result_state = "rated"
        else:
            PackageRating.objects.filter(rater=self.user, package=self.package).delete()
            result_state = "unrated"
        return (result_state, self.package.rating_score)
