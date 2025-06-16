from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()

if not hasattr(User, "moderated_communities"):

    def moderated_communities(self):
        if not hasattr(self, "_moderated_communities"):
            from thunderstore.repository.views.package._utils import (
                get_moderated_communities,
            )

            print("Should run once ever")
            self._moderated_communities = get_moderated_communities(self)
        return self._moderated_communities

    User.moderated_communities = property(moderated_communities)

AnonymousUser.moderated_communities = []
