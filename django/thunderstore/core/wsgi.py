import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thunderstore.core.settings")

application = get_wsgi_application()

from django.conf import settings

if settings.ENABLE_DEBUGPY:
    import debugpy

    debugpy.listen(("0.0.0.0", 5678))

import thunderstore.monkeypatch  # noqa
