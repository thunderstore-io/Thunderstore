

class ChoiceEnum(object):

    @classmethod
    def as_choices(cls):
        return [
            (key, value)
            for key, value in vars(cls).items()
            if not key.startswith("_")
        ]

    @classmethod
    def options(cls):
        return [
            value
            for key, value in vars(cls).items()
            if not key.startswith("_")
        ]
