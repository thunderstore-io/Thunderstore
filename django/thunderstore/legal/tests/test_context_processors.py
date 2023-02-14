import pytest

from django_contracts.models import LegalContract, LegalContractVersion
from thunderstore.legal.context_processors import legal_contracts


@pytest.mark.django_db
def test_legal_contracts_context_processor(
    published_legal_contract_version: LegalContractVersion,
):
    published_contract = published_legal_contract_version.contract
    unpublished_contract = LegalContract.objects.create(
        slug="unpublished", title="Unpublished"
    )
    v1 = LegalContractVersion.objects.create(contract=unpublished_contract)
    v1.publish()
    versionless_contract = LegalContract.objects.create(
        slug="versionless", title="Versionless"
    )
    versionless_contract.publish()
    result = legal_contracts(None)
    assert "legal_contracts" in result
    contracts = result["legal_contracts"]
    assert contracts.count() == 1
    assert published_contract in contracts
    assert versionless_contract not in contracts
    assert unpublished_contract not in contracts
