import importlib
import importlib.util
import inspect
import pkgutil
from typing import Set, Type

from .base import BasePlugin


def load_ts_plugins() -> Set[Type[BasePlugin]]:
    plugin_modules = {
        name: importlib.import_module(f"{name}.ts_plugins")
        for finder, name, ispkg in pkgutil.iter_modules()
        if name.startswith("ts_") and importlib.util.find_spec(f"{name}.ts_plugins")
    }
    modules = (x[1] for x in plugin_modules.items())
    plugins = set()
    for module in modules:
        for name, member in inspect.getmembers(module, inspect.isclass):
            if issubclass(member, BasePlugin) and member is not BasePlugin:
                plugins.add(member)

    print(f"Loaded {len(plugins)} plugins:")
    for plugin in plugins:
        print(f"- {plugin.__name__}")
    return plugins
