from django import forms
from django.urls import reverse_lazy
from django.views.generic.edit import FormView


class LinkedAccountDisconnectForm(forms.Form):
    provider = forms.CharField()


class LinkedAccountsView(FormView):
    template_name = "settings/linked_accounts.html"
    form_class = LinkedAccountDisconnectForm
    success_url = reverse_lazy("settings.linked-accounts")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["can_disconnect"] = self.can_disconnect
        context["page_title"] = "Linked Accounts"
        return context

    @property
    def can_disconnect(self):
        return self.request.user.social_auth.count() > 1

    def disconnect_account(self, provider):
        if not self.can_disconnect:
            return
        social_auth = self.request.user.social_auth.filter(provider=provider).first()
        social_auth.delete()

    def form_valid(self, form):
        self.disconnect_account(form.cleaned_data["provider"])
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


class DeleteAccountView(FormView):
    template_name = "settings/delete_account.html"
    form_class = DeleteAccountForm
    success_url = reverse_lazy("index")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Delete Account"
        return context

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.request.user.delete()
        return super().form_valid(form)
