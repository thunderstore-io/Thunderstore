from sentry_sdk import capture_exception as capture_sentry_exception


class ChoiceEnum(object):
    @classmethod
    def as_choices(cls):
        return [
            (key, value)
            for key, value in vars(cls).items()
            if not key.startswith("_")
            and any(
                (
                    isinstance(value, str),
                    isinstance(value, int),
                    isinstance(value, float),
                    isinstance(value, list),
                    isinstance(value, dict),
                )
            )
        ]

    @classmethod
    def options(cls):
        return [
            value
            for key, value in vars(cls).items()
            if not key.startswith("_")
            and any(
                (
                    isinstance(value, str),
                    isinstance(value, int),
                    isinstance(value, float),
                    isinstance(value, list),
                    isinstance(value, dict),
                )
            )
        ]


def ensure_fields_editable_on_creation(readonly_fields, obj, editable_fields):
    if obj:
        return readonly_fields
    else:
        # Creating the object so make restaurant editable
        return list(x for x in readonly_fields if x not in editable_fields)


class CommunitySiteSerializerContext:
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["community_site"] = self.request.community_site
        return context


def capture_exception(*args, **kwargs):
    capture_sentry_exception(*args, **kwargs)
