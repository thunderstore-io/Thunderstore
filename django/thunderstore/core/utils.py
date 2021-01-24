class ChoiceEnum(object):
    @classmethod
    def as_choices(cls):
        return [
            (key, value) for key, value in vars(cls).items() if not key.startswith("_")
        ]

    @classmethod
    def options(cls):
        return [value for key, value in vars(cls).items() if not key.startswith("_")]


def ensure_fields_editable_on_creation(readonly_fields, obj, editable_fields):
    if obj:
        return readonly_fields
    else:
        # Creating the object so make restaurant editable
        return [x for x in readonly_fields if x not in editable_fields]


class CommunitySiteSerializerContext:
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["community_site"] = self.request.community_site
        return context
