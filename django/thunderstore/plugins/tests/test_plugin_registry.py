from django.urls import URLPattern

from thunderstore.plugins.base import BasePlugin
from thunderstore.plugins.registry import PluginRegistry, plugin_registry


def test_plugin_registry_return_types():
    assert isinstance(plugin_registry, PluginRegistry)
    assert isinstance(plugin_registry.plugins, set)

    assert isinstance(plugin_registry.get_django_settings({}), dict)
    assert isinstance(plugin_registry.get_installed_apps([]), list)
    assert isinstance(plugin_registry.get_settings_urls(), list)
    assert isinstance(plugin_registry.get_legacy_package_urls(), list)
    assert isinstance(plugin_registry.get_new_package_urls(), list)
    assert isinstance(plugin_registry.get_cyberstorm_api_urls(), list)
    assert isinstance(plugin_registry.get_settings_links(), list)


def test_base_plugin_return_types():
    base_plugin = BasePlugin()
    assert isinstance(base_plugin.get_django_settings({}), dict)
    assert isinstance(base_plugin.get_settings_urls(), list)
    assert isinstance(base_plugin.get_legacy_package_urls(), list)
    assert isinstance(base_plugin.get_new_package_urls(), list)
    assert isinstance(base_plugin.get_cyberstorm_api_urls(), list)
    assert isinstance(base_plugin.get_settings_links(), list)


def test_plugin_registry_get_new_package_urls():
    urls = plugin_registry.get_new_package_urls()
    if plugin_registry.plugins:
        for url in urls:
            assert isinstance(url, URLPattern)
    else:
        assert urls == []


def test_plugin_registry_get_cyberstorm_api_urls():
    urls = plugin_registry.get_cyberstorm_api_urls()
    if plugin_registry.plugins:
        for url in urls:
            assert isinstance(url, URLPattern)
    else:
        assert urls == []
