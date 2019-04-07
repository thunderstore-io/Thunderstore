import os

from whitenoise import WhiteNoise

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

application = get_wsgi_application()

from django.conf import settings  # noqa

import monkeypatch  # noqa

application = WhiteNoise(application, root=settings.STATIC_ROOT)
