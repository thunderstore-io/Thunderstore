from django import forms
from django.core.exceptions import ValidationError
from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from thunderstore.api.cyberstorm.services.user import (
    delete_user_account,
    delete_user_social_auth,
)
from thunderstore.core.mixins import RequireAuthenticationMixin
from thunderstore.core.types import UserType
from thunderstore.frontend.views import SettingsViewMixin
from thunderstore.repository.models import TeamMember


class LinkedAccountDisconnectForm(forms.Form):
    provider = forms.CharField()

    def disconnect_account(self, provider: str, user: UserType):
        social_auth = user.social_auth.filter(provider=provider).first()
        if not social_auth:
            raise Http404("Social auth not found")

        try:
            delete_user_social_auth(social_auth=social_auth)
        except ValidationError as e:
            self.add_error(None, e)


class LinkedAccountsView(SettingsViewMixin, RequireAuthenticationMixin, FormView):
    template_name = "settings/linked_accounts.html"
    form_class = LinkedAccountDisconnectForm
    success_url = reverse_lazy("settings.linked-accounts")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_disconnect"] = self.can_disconnect
        context["page_title"] = "Linked Accounts"
        return context

    @property
    def can_disconnect(self):
        return self.request.user.social_auth.count() > 1

    def form_valid(self, form):
        form.disconnect_account(form.cleaned_data["provider"], self.request.user)
        if form.errors:
            return self.form_invalid(form)
        return super().form_valid(form)


class DeleteAccountForm(forms.Form):
    verification = forms.CharField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

    def clean_verification(self):
        data = self.cleaned_data["verification"]
        if data != self.user.username:
            raise forms.ValidationError("Invalid verification")
        return data

    def delete_user(self):
        delete_user_account(target_user=self.user)


class DeleteAccountView(SettingsViewMixin, RequireAuthenticationMixin, FormView):
    template_name = "settings/delete_account.html"
    form_class = DeleteAccountForm
    success_url = reverse_lazy("index")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Delete Account"
        context["team_names"] = ", ".join(
            TeamMember.objects.filter(
                user=self.request.user,
                team__is_active=True,
            ).values_list("team__name", flat=True)
        )
        return context

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.delete_user()
        return super().form_valid(form)
