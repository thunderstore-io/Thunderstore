import factory
from factory.django import DjangoModelFactory

from thunderstore.modpacks.models import LegacyProfile

LEGACYPROFILE_TEST_CONTENT = b"test content"


class LegacyProfileFactory(DjangoModelFactory):
    class Meta:
        model = LegacyProfile

    file = factory.django.FileField(data=LEGACYPROFILE_TEST_CONTENT)
    file_size = len(LEGACYPROFILE_TEST_CONTENT)
