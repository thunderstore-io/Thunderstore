import pytest

from django_contracts.models import LegalContract, LegalContractVersion


@pytest.mark.django_db
def test_contract_publishing():
    contract = LegalContract.objects.create(slug="contract", title="Contract")

    v1 = LegalContractVersion.objects.create(contract=contract)
    v2 = LegalContractVersion.objects.create(contract=contract)

    assert str(v1) == f"Contract - {v1.datetime_created.isoformat()} - DRAFT"

    assert contract.latest is None
    assert v2.is_latest is False
    assert v2.effective_date == v2.datetime_updated
    assert v2.datetime_published is None
    v2.publish()
    v1.refresh_from_db()
    v2.refresh_from_db()
    contract.refresh_from_db()
    assert contract.latest == v2
    assert v2.is_latest is True
    assert v2.datetime_published > v2.datetime_created
    assert v2.effective_date == v2.datetime_published

    assert v1.is_latest is False
    assert v1.datetime_published is None
    v1.publish()
    v1.refresh_from_db()
    v2.refresh_from_db()
    contract.refresh_from_db()
    assert contract.latest == v1
    assert v2.is_latest is False
    assert v1.is_latest is True
    assert v1.datetime_published > v1.datetime_created
    assert v1.effective_date == v1.datetime_published


@pytest.mark.django_db
def test_contract_meta():
    contract = LegalContract.objects.create(slug="contract", title="Contract")
    assert str(contract) == "Contract"
    assert contract.get_absolute_url() is not None
    ver = LegalContractVersion.objects.create(contract=contract)
    assert str(ver) == f"Contract - {ver.datetime_created.isoformat()} - DRAFT"
    assert contract.get_absolute_url() is not None
