from factory.django import DjangoModelFactory

from thunderstore.permissions.models import VisibilityFlags


class VisibilityFlagsFactory(DjangoModelFactory):
    class Meta:
        model = VisibilityFlags

    public_list = True
    public_detail = True
    owner_list = True
    owner_detail = True
    moderator_list = True
    moderator_detail = True
    admin_list = True
    admin_detail = True
