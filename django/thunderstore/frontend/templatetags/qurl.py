from typing import Any, List, Set

from django.template import Library, Node, TemplateSyntaxError
from django.utils.http import urlencode

register = Library()


class QurlNode(Node):
    def __init__(
        self,
        allowed_params_key: str,
        param_key: str,
        param_val: Any,
        removals: List[str],
    ):
        self.allowed_params_key = allowed_params_key
        self.param_key = param_key
        self.param_val = param_val
        self.removals = removals

    def render(self, context):
        request = context["request"]
        params = request.GET.copy()
        params.setlist(self.param_key, [self.param_val.resolve(context)])
        allowed_params = context[self.allowed_params_key]
        for key, _ in request.GET.items():
            if key not in allowed_params:
                params.pop(key)
        for entry in self.removals:
            try:
                params.pop(entry)
            except KeyError:
                pass
        return f"{request.path}?{urlencode(params, True)}"


@register.tag("qurl")
def qurl(parser, token):
    tokens = token.split_contents()

    if len(tokens) < 4 or len(tokens) > 5:
        raise TemplateSyntaxError("'%r' tag requires 3 or 4 arguments." % tokens[0])

    removals = []
    if len(tokens) == 5:
        removals = str(tokens[4]).split(",")

    return QurlNode(
        allowed_params_key=tokens[1],
        param_key=tokens[2],
        param_val=parser.compile_filter(tokens[3]),
        removals=removals,
    )
