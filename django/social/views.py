from django.conf import settings
from django.views.generic.detail import DetailView


class LinkedAccountsView(DetailView):
    model = settings.AUTH_USER_MODEL
    template_name = "social/profile_detail.html"

    def get_object(self, *args, **kwargs):
        return self.request.user

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        return context
