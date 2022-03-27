import sys

from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class StubStorage(Storage):
    pass


def is_makemigrations_check() -> bool:
    return (
        len(sys.argv) >= 2
        and sys.argv[0] == "manage.py"
        and sys.argv[1] == "makemigrations"
    )
