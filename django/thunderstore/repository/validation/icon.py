import io

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image

MAX_ICON_SIZE = 1024 * 1024 * 6


def validate_icon(icon_data: bytes) -> ContentFile:
    try:
        icon = ContentFile(icon_data)
    except Exception:
        raise ValidationError("Unknown error while processing icon.png")

    if icon.size > MAX_ICON_SIZE:
        raise ValidationError(
            f"icon.png filesize is too big, current maximum is {MAX_ICON_SIZE} bytes",
        )

    try:
        image = Image.open(io.BytesIO(icon_data))
    except Exception:
        raise ValidationError("Unsupported or corrupt icon, must be png")

    if image.format != "PNG":
        raise ValidationError("Icon must be in png format")

    if not (image.size[0] == 256 and image.size[1] == 256):
        raise ValidationError("Invalid icon dimensions, must be 256x256")

    return icon
