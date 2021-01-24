from rest_framework.authentication import TokenAuthentication as DRFTokenAuthentication


class TokenAuthentication(DRFTokenAuthentication):
    keyword = "Bearer"
