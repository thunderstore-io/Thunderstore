from django.template import Library, Node, TemplateSyntaxError
from django.utils.http import urlencode

register = Library()


class QurlNode(Node):
    def __init__(self, param_key, param_val):
        self.param_key = param_key
        self.param_val = param_val

    def render(self, context):
        request = context["request"]
        params = request.GET.dict()
        params[self.param_key] = self.param_val.resolve(context)
        return f"{request.path}?{urlencode(params)}"


@register.tag("qurl")
def qurl(parser, token):
    tokens = token.split_contents()

    if len(tokens) != 3:
        raise TemplateSyntaxError("'%r' tag requires 2 arguments." % tokens[0])

    return QurlNode(
        param_key=tokens[1],
        param_val=parser.compile_filter(tokens[2]),
    )
