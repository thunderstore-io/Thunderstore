from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django import forms


class LinkedAccountDisconnectForm(forms.Form):
    provider = forms.CharField()


class LinkedAccountsView(FormView):
    template_name = "settings/linked_accounts.html"
    form_class = LinkedAccountDisconnectForm
    success_url = reverse_lazy("settings.linked-accounts")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["can_disconnect"] = self.can_disconnect
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
