from rest_framework import serializers


class EmptyStringAsNoneField(serializers.Field):
    """
    Serialize empty string to None and deserialize vice versa.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_null = True
        self.allow_blank = True

    def to_representation(self, value):
        return None if value == "" else value

    def to_internal_value(self, data):
        return "" if data is None else data
