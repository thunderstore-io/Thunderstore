from django.db import models
from django.db.models.fields.related_descriptors import ReverseOneToOneDescriptor


class SafeReverseOnetoOneDescriptor(ReverseOneToOneDescriptor):
    def __get__(self, *args, **kwargs):
        try:
            return super().__get__(*args, **kwargs)
        except self.RelatedObjectDoesNotExist:
            return None


class SafeOneToOneOrField(models.OneToOneField):
    """
    Same as OneToOneField but returns None instead of raising an exception if
    the relation doesn't exist.
    """

    related_accessor_class = SafeReverseOnetoOneDescriptor
