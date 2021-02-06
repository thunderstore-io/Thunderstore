from django.utils import timezone
from rest_framework.authentication import TokenAuthentication as DRFTokenAuthentication
from rest_framework.authtoken.models import Token

from thunderstore.account.models import ServiceAccount


class TokenAuthentication(DRFTokenAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        out = super().authenticate(request)
        if out is not None and all(out):
            # The request has been authenticated
            token: Token = out[1]
            service_account = ServiceAccount.objects.filter(user=token.user).first()
            if service_account:
                service_account.last_used = timezone.now()
                service_account.save(update_fields=("last_used",))
        return out
