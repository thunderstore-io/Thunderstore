from django.template import (
    Library, Node, TemplateSyntaxError, VariableDoesNotExist,
)

from core.cache import (
    DEFAULT_CACHE_EXPIRY, get_cache_key, cache_get_or_set,
)


register = Library()


class CacheNode(Node):

    def __init__(self, nodelist, cache_bust_condition, fragment_name, expiry, vary_on):
        self.nodelist = nodelist
        self.cache_bust_condition = cache_bust_condition
        self.expiry = expiry
        self.fragment_name = fragment_name
        self.vary_on = vary_on

    def render(self, context):
        try:
            cache_until = self.cache_bust_condition.resolve(context)
        except VariableDoesNotExist:
            raise TemplateSyntaxError(f'"cache_until" tag got an unknown variable: {self.cache_bust_condition.var}')

        try:
            expire_time = self.expiry.resolve(context)
        except VariableDoesNotExist:
            raise TemplateSyntaxError(f'"cache_until" tag got an unknown variable: {self.expire_time.var}')

        if expire_time is not None:
            try:
                expire_time = int(expire_time)
            except (ValueError, TypeError):
                raise TemplateSyntaxError(f'"cache_until" tag got a non-integer expiry value: {expire_time}')

        vary_on = [var.resolve(context) for var in self.vary_on]

        return cache_get_or_set(
            key=get_cache_key(
                cache_bust_condition=cache_until,
                cache_type="template",
                key=self.fragment_name,
                vary_on=vary_on,
            ),
            default=lambda: self.nodelist.render(context),
            expiry=expire_time,
        )


@register.tag("cache_until")
def do_cache(parser, token):
    """
    This will cache the contents of a template fragment until the cache is
    busted by the cache bust condition or timeout.
    Usage::
        {% load cache_until %}
        {% cache_until [cache_bust_condition] [fragment_name] [timeout] %}
            .. some expensive processing ..
        {% endcache %}
    This tag also supports varying by a list of arguments::
        {% load cache_until %}
        {% cache_until [cache_bust_condition] [fragment_name] [timeout] [var1] [var2] .. %}
            .. some expensive processing ..
        {% endcache %}
    Each unique set of arguments will result in a unique cache entry.
    """
    nodelist = parser.parse(("endcache",))
    parser.delete_first_token()
    tokens = token.split_contents()

    if len(tokens) < 3:
        raise TemplateSyntaxError("'%r' tag requires at least 2 arguments." % tokens[0])

    expiry = DEFAULT_CACHE_EXPIRY
    if len(tokens) > 3:
        expiry = parser.compile_filter(tokens[3])

    return CacheNode(
        nodelist=nodelist,
        cache_bust_condition=parser.compile_filter(tokens[1]),
        fragment_name=tokens[2],
        expiry=expiry,
        vary_on=[parser.compile_filter(t) for t in tokens[4:]],
    )
