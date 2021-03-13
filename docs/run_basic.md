# Running a basic version

This is useful when developing the [React frontend](https://github.com/thunderstore-io/thunderstore-ui), especially if an API endpoint is not in production yet.

You can get the Docker tag from the GitHub Actions logs or just use the commit SHA1. If tests fail, an image will not be pushed.

```
COMMIT_SHA=... docker-compose up -f docker/docker-compose.basic.yml
```

To set up the instance, run in the container:

-   `python manage.py migrate`
-   `python manage.py createsuperuser` (this is interactive)
-   `python manage.py shell` (this is interactive)

In the Python shell, run:

```python
from django.contrib.sites.models import Site
from thunderstore.community.models import CommunitySite
site = Site.objects.create(domain="localhost", name="Site Name")
community_site = CommunitySite.objects.first()
community_site.site = site
community_site.save()
```

You may need to replace `localhost` with the domain you are using.

You can now access the Django admin page at `http://localhost/djangoadmin/`.
