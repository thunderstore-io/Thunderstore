from social_django.strategy import DjangoStrategy


class CommunitySocialAuthStrategy(DjangoStrategy):

    @property
    def is_discord_configured(self):
        return (
            self.request.community_site and
            self.request.community_site.social_auth_discord_key and
            self.request.community_site.social_auth_discord_secret
        )

    @property
    def is_github_configured(self):
        return (
            self.request.community_site and
            self.request.community_site.social_auth_github_key and
            self.request.community_site.social_auth_github_secret
        )

    def get_setting(self, name):
        if name == "SOCIAL_AUTH_GITHUB_KEY" and self.is_github_configured:
            return self.request.community_site.social_auth_github_key
        elif name == "SOCIAL_AUTH_GITHUB_SECRET" and self.is_github_configured:
            return self.request.community_site.social_auth_github_secret
        elif name == "SOCIAL_AUTH_DISCORD_KEY" and self.is_discord_configured:
            return self.request.community_site.social_auth_discord_key
        elif name == "SOCIAL_AUTH_DISCORD_SECRET" and self.is_discord_configured:
            return self.request.community_site.social_auth_discord_secret
        return super().get_setting(name)
