from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


def _get_moderated_communities(user):
    from thunderstore.repository.views.package._utils import get_moderated_communities

    return get_moderated_communities(user)


if not hasattr(User, "moderated_communities"):

    def moderated_communities(self):
        if hasattr(self, "_moderated_communities"):
            return self._moderated_communities

        if not self.is_authenticated:
            self._moderated_communities = []
            return self._moderated_communities

        if self.is_staff or self.is_superuser:
            self._moderated_communities = _get_moderated_communities(self)
            return self._moderated_communities

        from thunderstore.account.models import UserMeta

        try:
            user_meta = UserMeta.objects.only("can_moderate_any_community").get(
                user=self
            )
            if user_meta.can_moderate_any_community:
                communities = _get_moderated_communities(self)
            else:
                communities = []
        except UserMeta.DoesNotExist:
            communities = []

        self._moderated_communities = communities
        return communities

    User.moderated_communities = property(moderated_communities)

AnonymousUser.moderated_communities = []
