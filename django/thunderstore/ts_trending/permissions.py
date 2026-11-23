from django.conf import settings

from thunderstore.social.permissions import SharedSecretPermission


class TrendingSharedSecretPermission(SharedSecretPermission):
    """
    For receiving trending scores from the query service.
    """

    SHARED_SECRET = settings.TRENDING_SHARED_SECRET
