import pytest
from django.core.exceptions import ValidationError

from thunderstore.repository.models import Namespace


@pytest.mark.django_db
def test_namespace_name_case_insensitive(team):
    Namespace.objects.create(name="test_namespace", team=team)
    with pytest.raises(ValidationError) as exc:
        Namespace.objects.create(name="tEsT_NaMeSpAcE", team=team)
    assert "The namespace name already exists" in str(exc.value)


@pytest.mark.django_db
def test_namespace___str__(team):
    ns = Namespace(name="Test_Namespace", team=team)
    assert ns.__str__() == "Test_Namespace"


@pytest.mark.django_db
def test_namespace_validate(team):
    ns = Namespace(name="test_namespace", team=team)
    assert ns._state.adding is True
    ns.save()
    assert ns._state.adding is False
    ns.validate()
    with pytest.raises(ValidationError) as exc:
        Namespace.objects.create(name="tEsT_NaMeSpAcE", team=team)
    assert "The namespace name already exists" in str(exc.value)
