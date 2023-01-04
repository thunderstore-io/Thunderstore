import pytest
from django.core.exceptions import ValidationError

from thunderstore.repository.validation.markdown import (
    MAX_MARKDOWN_SIZE,
    validate_markdown,
)


@pytest.mark.parametrize("name", ("README.md", "CHANGELOG.md"))
def test_validate_markdown_unicode_error(name: str) -> None:
    readme = bytes.fromhex("8081")
    with pytest.raises(
        ValidationError,
        match=f"Make sure the {name} is UTF-8 compatible",
    ):
        validate_markdown(name, readme)


@pytest.mark.parametrize("name", ("README.md", "CHANGELOG.md"))
def test_validate_markdown_too_long(name) -> None:
    readme = ("a" * (MAX_MARKDOWN_SIZE + 1)).encode("utf-8")
    with pytest.raises(
        ValidationError,
        match=f"{name} is too long, max: {MAX_MARKDOWN_SIZE}",
    ):
        validate_markdown(name, readme)


def test_validate_markdown_has_bom() -> None:
    readme = str.encode("", encoding="utf-8-sig")
    with pytest.raises(
        ValidationError,
        match="UTF-8 BOM",
    ):
        validate_markdown("README.md", readme)


def test_validate_markdown_pass() -> None:
    readme = ("a" * (MAX_MARKDOWN_SIZE)).encode("utf-8")
    assert isinstance(validate_markdown("README.md", readme), str)
