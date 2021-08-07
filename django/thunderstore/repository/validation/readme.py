from django.core.exceptions import ValidationError

MAX_README_SIZE = 32768


def validate_readme(readme_data: bytes) -> str:
    try:
        readme = readme_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(
            [
                f"Unable to parse README.md: {exc}\n",
                "Make sure the README.md is UTF-8 compatible",
            ],
        )
    if len(readme) > MAX_README_SIZE:
        raise ValidationError(f"README.md is too long, max: {MAX_README_SIZE}")

    return readme
