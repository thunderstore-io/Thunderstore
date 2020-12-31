from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def get_install_url(context, package_version):
    return package_version.get_install_url(context["request"])
