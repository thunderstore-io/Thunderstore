from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def get_install_url(context, obj):
    return obj.get_install_url(context["request"])


@register.simple_tag(takes_context=True)
def get_download_url(context, obj):
    return obj.download_url(context["community_identifier"])


@register.simple_tag(takes_context=True)
def get_absolute_url(context, obj):
    return obj.get_absolute_url(context["community_identifier"])


@register.simple_tag(takes_context=True)
def get_owner_url(context, obj):
    return obj.owner_url(context["community_identifier"])
