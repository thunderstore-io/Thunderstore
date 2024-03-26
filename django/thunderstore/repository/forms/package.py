from typing import Optional

from django import forms
from django.contrib.auth import get_user_model

from thunderstore.core.types import UserType
from thunderstore.repository.models import Package

User = get_user_model()


class DeprecateForm(forms.ModelForm):
    class Meta:
        model = Package
        fields = ["is_deprecated"]

    def __init__(self, user: Optional[UserType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        self.instance.can_user_manage_deprecation(self.user)
        return super().clean()

    def execute(self):
        desired_state = self.cleaned_data.get("is_deprecated")
        if desired_state:
            self.instance.deprecate()
        else:
            self.instance.undeprecate()
        return self.instance
