from typing import List

from django.template import Library, Node, TemplateSyntaxError
from django.utils.http import urlencode

register = Library()


class QurlNode(Node):
    def __init__(self, param_key, param_val, removals: List[str]):
        self.param_key = param_key
        self.param_val = param_val
        self.removals = removals

    def render(self, context):
        request = context["request"]
        community_site = context["community_site"]
        params = request.GET.copy()
        params.setlist(self.param_key, [self.param_val.resolve(context)])
        for entry in self.removals:
            try:
                params.pop(entry)
            except KeyError:
                pass
        return f"{community_site.get_absolute_url}?{urlencode(params, True)}"


@register.tag("qurl")
def qurl(parser, token):
    tokens = token.split_contents()

    if len(tokens) < 3 or len(tokens) > 4:
        raise TemplateSyntaxError("'%r' tag requires 2 or 3 arguments." % tokens[0])

    removals = []
    if len(tokens) == 4:
        removals = str(tokens[3]).split(",")

    return QurlNode(
        param_key=tokens[1],
        param_val=parser.compile_filter(tokens[2]),
        removals=removals,
    )
