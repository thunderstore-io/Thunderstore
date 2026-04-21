from django import template
from django.utils.http import urlencode

register = template.Library()


@register.simple_tag(takes_context=True)
def qurl(context, param_key, param_val, *remove_keys):
    view = context.get("view")
    if not view or not hasattr(view, "get_clean_params"):
        return ""

    params = view.get_clean_params()
    for key in remove_keys:
        params.pop(key, None)

    params[param_key] = param_val

    return f"{view.request.path}?{urlencode(params, doseq=True)}"
