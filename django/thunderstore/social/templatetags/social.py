from django import template

register = template.Library()


def extract_social_auth_username(social_auth):
    if social_auth.provider == "discord":
        username = social_auth.extra_data.get("username", "")
        discriminator = social_auth.extra_data.get("discriminator", "")
        if username and discriminator:
            return f"{username}#{discriminator}"
    if social_auth.provider == "github":
        username = social_auth.extra_data.get("login", "")
        if username:
            return f"{username}"
    return ""


def get_social_username(user, provider):
    social_auth = user.social_auth.filter(provider=provider).first()
    if not social_auth:
        return ""
    return extract_social_auth_username(social_auth)


@register.simple_tag
def social_username(user, provider):
    return get_social_username(user, provider)


@register.simple_tag
def social_auth_username(social_auth):
    return extract_social_auth_username(social_auth)
