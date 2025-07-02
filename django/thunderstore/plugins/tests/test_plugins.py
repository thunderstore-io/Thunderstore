from thunderstore.plugins.base import BasePlugin


def test_base_plugin_default_getters():
    assert BasePlugin.get_settings_links() == []
    assert BasePlugin.get_settings_urls() == []
    assert BasePlugin.get_moderation_urls() == []
    assert BasePlugin.get_legacy_package_urls() == []
    assert BasePlugin.get_new_package_urls() == []
