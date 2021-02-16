from django.core.exceptions import ValidationError

from thunderstore.core.utils import check_validity


def test_check_validity_fail():
    def fail_fn():
        raise ValidationError("test")

    assert check_validity(lambda: fail_fn()) is False


def test_check_validity_success():
    def success_fn():
        pass

    assert check_validity(lambda: success_fn()) is True
