from typing import List

import pytest
from django.conf import settings
from django.test import Client

from django_contracts.admin import publish
from django_contracts.models import LegalContract, LegalContractVersion, PublishStatus


@pytest.mark.django_db
def test_admin_legal_contract_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/contracts/legalcontract/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("publish_status", PublishStatus.values)
def test_admin_legal_contract_detail(
    admin_client: Client, published_legal_contract: LegalContract, publish_status: str
) -> None:
    published_legal_contract.publish_status = publish_status
    published_legal_contract.save()
    pk = published_legal_contract.pk
    path = f"/djangoadmin/contracts/legalcontract/{pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_legal_contract_version_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/contracts/legalcontractversion/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("publish_status", PublishStatus.values)
def test_admin_legal_contract_version_detail(
    admin_client: Client,
    published_legal_contract_version: LegalContractVersion,
    publish_status: str,
) -> None:
    published_legal_contract_version.publish_status = publish_status
    published_legal_contract_version.save()
    pk = published_legal_contract_version.pk
    path = f"/djangoadmin/contracts/legalcontractversion/{pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_actions_legal_contract_publish() -> None:
    contracts: List[LegalContract] = [
        LegalContract.objects.create(slug=f"contract-{i}", title=f"Contract {i}")
        for i in range(3)
    ]
    versions: List[LegalContractVersion] = [
        LegalContractVersion.objects.create(contract=contracts[0])
    ]
    assert all([x.publish_status == PublishStatus.DRAFT for x in contracts])
    assert all([x.publish_status == PublishStatus.DRAFT for x in versions])
    publish(None, None, LegalContract.objects.all())
    publish(None, None, LegalContractVersion.objects.all())
    [x.refresh_from_db() for x in contracts]
    [x.refresh_from_db() for x in versions]
    assert all([x.publish_status == PublishStatus.PUBLISHED for x in contracts])
    assert all([x.publish_status == PublishStatus.PUBLISHED for x in versions])
