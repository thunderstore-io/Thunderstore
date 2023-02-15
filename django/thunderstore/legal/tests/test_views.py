import pytest
from django.test import Client
from django.urls import reverse

from django_contracts.models import LegalContract, LegalContractVersion, PublishStatus
from thunderstore.community.models import CommunitySite
from thunderstore.core.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize("is_staff", (False, True))
def test_views_legal_contract_history_view(
    client: Client,
    published_legal_contract: LegalContract,
    community_site: CommunitySite,
    is_staff: bool,
):
    if is_staff:
        client.force_login(UserFactory.create(is_staff=True))

    old_version = LegalContractVersion.objects.create(contract=published_legal_contract)
    old_version.publish()
    published_version = LegalContractVersion.objects.create(
        contract=published_legal_contract
    )
    published_version.publish()
    LegalContractVersion.objects.create(contract=published_legal_contract)

    url = reverse(
        "contracts:contract.history", kwargs={"contract": published_legal_contract.slug}
    )
    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    text_result = response.content.decode("utf-8")
    assert '<span class="badge badge-pill badge-success">Active</span>' in text_result
    assert (
        '<span class="badge badge-pill badge-danger">Deprecated</span>' in text_result
    )
    has_draft = (
        '<span class="badge badge-pill badge-warning">Draft</span>' in text_result
    )
    assert has_draft == is_staff


@pytest.mark.django_db
def test_views_legal_contract_detail_view(
    client: Client, community_site: CommunitySite
):
    url = reverse("contracts:contract", kwargs={"contract": "test"})
    assert client.get(url, HTTP_HOST=community_site.site.domain).status_code == 404
    contract = LegalContract.objects.create(slug="test", title="Test")
    assert client.get(url, HTTP_HOST=community_site.site.domain).status_code == 404
    contract.publish()
    assert client.get(url, HTTP_HOST=community_site.site.domain).status_code == 404
    version = LegalContractVersion.objects.create(
        contract=contract, markdown_content="Test contract content"
    )
    assert client.get(url, HTTP_HOST=community_site.site.domain).status_code == 404
    version.publish()
    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    assert "Test contract content" in response.content.decode("utf-8")


@pytest.mark.django_db
@pytest.mark.parametrize("is_staff", (False, True))
def test_views_legal_contract_version_detail_view(
    client: Client,
    published_legal_contract_version: LegalContractVersion,
    community_site: CommunitySite,
    is_staff: bool,
):
    if is_staff:
        client.force_login(UserFactory.create(is_staff=True))

    version = published_legal_contract_version
    url = version.get_absolute_url()
    assert client.get(url, HTTP_HOST=community_site.site.domain).status_code == 200

    version.publish_status = PublishStatus.DRAFT
    version.save()
    assert client.get(url, HTTP_HOST=community_site.site.domain).status_code == 200

    version.contract.latest = None
    version.contract.save()
    assert (
        client.get(url, HTTP_HOST=community_site.site.domain).status_code == 200
        if is_staff
        else 404
    )
