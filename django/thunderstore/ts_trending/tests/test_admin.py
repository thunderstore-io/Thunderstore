import pytest
from django.conf import settings
from django.contrib import admin
from django.test import Client
from django.utils import timezone

from thunderstore.community.models import PackageListing
from thunderstore.ts_trending.models import NewAndTrendingScore, TrendingScore


@pytest.mark.django_db
@pytest.mark.parametrize("model", (TrendingScore, NewAndTrendingScore))
def test_admin_score_is_read_only(
    model,
    admin_client: Client,
    active_package_listing: PackageListing,
) -> None:
    score = model.objects.create(
        listing=active_package_listing,
        score=1.5,
        datetime_computed=timezone.now(),
    )
    modeladmin = admin.site._registry[model]
    path = f"/djangoadmin/ts_trending/{model._meta.model_name}/"

    list_resp = admin_client.get(path=path, HTTP_HOST=settings.PRIMARY_HOST)
    detail_resp = admin_client.get(
        path=f"{path}{score.pk}/change/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )

    assert list_resp.status_code == 200
    assert list_resp.context["cl"].result_count == 1
    assert detail_resp.status_code == 200
    assert str(score) in detail_resp.content.decode()
    request = list_resp.wsgi_request
    assert modeladmin.has_add_permission(request) is False
    assert modeladmin.has_change_permission(request) is False
