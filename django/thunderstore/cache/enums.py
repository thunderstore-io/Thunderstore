from thunderstore.core.utils import ChoiceEnum


# TODO: Support parameters in cache bust conditions (e.g. specific package update)
class CacheBustCondition(ChoiceEnum):
    background_update_only = "manual_update_only"
    any_package_updated = "any_package_updated"
    dynamic_html_updated = "dynamic_html_updated"
