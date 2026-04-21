from typing import Any, List, Optional, Set

from django.template import Library, Node, TemplateSyntaxError
from django.utils.http import urlencode

register = Library()


_MAX_DEFAULT_VALUE_LEN = 256


def _default_clean(value: str) -> Optional[str]:
    if value is None:
        return None
    if len(value) > _MAX_DEFAULT_VALUE_LEN:
        return None
    cleaned = "".join(ch for ch in value if ch >= " " and ch != "\x7f")
    return cleaned or None


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
        params = {}
        allowed_params = context[self.allowed_params_key]

        mapping_order = [
            ("q", "current_search"),
            ("ordering", "active_ordering"),
            ("section", "active_section"),
            ("included_categories", "included_categories"),
            ("excluded_categories", "excluded_categories"),
            ("nsfw", "nsfw_included"),
            ("deprecated", "deprecated_included"),
        ]

        for param_name, context_key in mapping_order:
            if param_name in allowed_params:
                val = context.get(context_key)
                if val:
                    if isinstance(val, (list, set)):
                        params[param_name] = sorted(list(val))
                    else:
                        params[param_name] = "on" if val is True else val

        if self.param_key in allowed_params:
            params[self.param_key] = self.param_val.resolve(context)

        for entry in self.removals:
            params.pop(entry, None)

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
