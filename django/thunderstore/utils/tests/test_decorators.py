import pytest
from django.db import transaction

from thunderstore.utils.decorators import run_after_commit


@pytest.mark.django_db(transaction=True)
def test_utils_run_after_commit():
    calls = []

    @run_after_commit
    def test_fn():
        calls.append(1)

    with transaction.atomic():
        assert len(calls) == 0
        test_fn()
        assert len(calls) == 0
    assert len(calls) == 1
    test_fn()
    assert len(calls) == 2
