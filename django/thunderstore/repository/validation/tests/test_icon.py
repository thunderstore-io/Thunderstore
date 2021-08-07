import io
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image

from thunderstore.repository.validation.icon import MAX_ICON_SIZE, validate_icon


@pytest.mark.parametrize(
    ("width", "height"),
    [
        (257, 256),
        (256, 257),
    ],
)
def test_validate_invalid_icon_dimensions(width: int, height: int) -> None:
    img = Image.new("RGB", (width, height), color="red")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")

    with pytest.raises(
        ValidationError,
        match="Invalid icon dimensions, must be 256x256",
    ):
        validate_icon(img_buffer.getvalue())


def test_validate_icon_too_large_file() -> None:
    img = Image.new("RGB", (256, 256), color="red")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.write(bytearray(MAX_ICON_SIZE))

    with pytest.raises(
        ValidationError,
        match=f"icon.png filesize is too big, current maximum is {MAX_ICON_SIZE} bytes",
    ):
        validate_icon(img_buffer.getvalue())


@pytest.mark.parametrize(
    "save_format",
    [
        "JPEG",
        "BMP",
        "WEBP",
        "GIF",
        "ICO",
    ],
)
def test_validate_icon_not_png_format(save_format: str) -> None:
    img = Image.new("RGB", (256, 256), color="red")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format=save_format)

    with pytest.raises(
        ValidationError,
        match="Icon must be in png format",
    ):
        validate_icon(img_buffer.getvalue())


def test_validate_icon_garbage_data() -> None:
    img_buffer = io.BytesIO()
    img_buffer.write(bytearray(MAX_ICON_SIZE))

    with pytest.raises(
        ValidationError,
        match="Unsupported or corrupt icon, must be png",
    ):
        validate_icon(img_buffer.getvalue())


def test_validate_icon_unreadable_input() -> None:
    test: Any = {"this is a dict": "not a readable file"}
    with pytest.raises(
        ValidationError,
        match="Unknown error while processing icon.png",
    ):
        validate_icon(test)


def test_validate_icon_valid_icon() -> None:
    img = Image.new("RGB", (256, 256), color="red")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    assert isinstance(validate_icon(img_buffer.getvalue()), ContentFile)
