import codecs

from django.core.exceptions import ValidationError

MAX_MARKDOWN_SIZE = 1000 * 100  # 100kb


def validate_markdown(filename: str, readme_data: bytes) -> str:
    try:
        readme = readme_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(
            [
                f"Unable to parse {filename}: {exc}\n",
                f"Make sure the {filename} is UTF-8 compatible",
            ],
        )
    if len(readme) > MAX_MARKDOWN_SIZE:
        raise ValidationError(f"{filename} is too long, max: {MAX_MARKDOWN_SIZE}")
    if readme_data.startswith(codecs.BOM_UTF8):
        raise ValidationError(
            f"{filename} starts with a UTF-8 BOM, please try to re-save the file without a BOM.",
        )

    return readme
