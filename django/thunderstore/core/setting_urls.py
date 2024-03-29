from thunderstore.plugins.registry import plugin_registry
from thunderstore.repository.urls import settings_urls as repository_settings_urls
from thunderstore.social.urls import settings_urls as social_settings_urls

settings_urls = (
    social_settings_urls
    + repository_settings_urls
    + plugin_registry.get_settings_urls()
)
