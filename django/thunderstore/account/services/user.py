from django.db import transaction
from social_django.models import UserSocialAuth

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType


@transaction.atomic
def delete_user_account(target_user: UserType):
    return target_user.delete()


@transaction.atomic
def delete_user_social_auth(social_auth: UserSocialAuth):
    target_user = social_auth.user

    auth_qs = UserSocialAuth.objects.select_for_update().filter(user=target_user)
    count = auth_qs.count()

    if count <= 1:
        raise PermissionValidationError("Cannot disconnect last linked auth method")

    return auth_qs.filter(pk=social_auth.pk).delete()
