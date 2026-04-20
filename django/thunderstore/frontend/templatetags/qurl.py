from typing import Any, Callable, Dict, List, Optional

from django.http import QueryDict
from django.template import Library, Node, TemplateSyntaxError
from django.utils.http import urlencode

register = Library()


# Default safety net applied to any query-string value for which the caller
# did not register a per-key validator. It is intentionally permissive so it
# does not silently break existing pagination for non-ASCII search text, but
# it still drops control characters and excessively long values, which is
# enough to prevent the "template fragment cache poisoning via reflected
# query value" class of bug.
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
        allowed_params = context[self.allowed_params_key]
        validators: Dict[str, Callable[[str], Optional[str]]] = context.get(
            f"{self.allowed_params_key}_validators", {}
        )

        # Build the output QueryDict from scratch. Only keys explicitly in the
        # allow-list, whose values pass either a caller-provided validator or
        # the conservative default, survive into the rendered href. This is
        # what stops reflected-value cache poisoning: no unvalidated input
        # from request.GET can be baked into a cached pagination link.
        params = QueryDict(mutable=True)
        for key in allowed_params:
            if key in self.removals or key == self.param_key:
                continue
            raw_values = request.GET.getlist(key)
            validator = validators.get(key, _default_clean)
            clean: List[str] = []
            for raw in raw_values:
                try:
                    cleaned = validator(raw)
                except (ValueError, TypeError):
                    continue
                if cleaned is None:
                    continue
                clean.append(str(cleaned))
            if clean:
                params.setlist(key, clean)

        resolved = self.param_val.resolve(context)
        if resolved is not None:
            params.setlist(self.param_key, [resolved])

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
