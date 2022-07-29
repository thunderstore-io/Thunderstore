import pytest
from django.core.exceptions import ValidationError

from thunderstore.repository.validation.readme import MAX_README_SIZE, validate_readme


def test_validate_readme_unicode_error() -> None:
    readme = bytes.fromhex("8081")
    with pytest.raises(
        ValidationError,
        match="Make sure the README.md is UTF-8 compatible",
    ):
        validate_readme(readme)


def test_validate_readme_too_long() -> None:
    readme = ("a" * (MAX_README_SIZE + 1)).encode("utf-8")
    with pytest.raises(
        ValidationError,
        match=f"README.md is too long, max: {MAX_README_SIZE}",
    ):
        validate_readme(readme)


def test_validate_readme_has_bom() -> None:
    readme = str.encode("", encoding="utf-8-sig")
    with pytest.raises(
        ValidationError,
        match="UTF-8 BOM",
    ):
        validate_readme(readme)


def test_validate_readme_pass() -> None:
    readme = ("a" * (MAX_README_SIZE)).encode("utf-8")
    assert isinstance(validate_readme(readme), str)
