import pytest

from thunderstore.usermedia.api.experimental.serializers.upload import FilenameField


@pytest.mark.parametrize(
    ["filename", "expected"],
    [
        ("asd/dsa", "dsa"),
        ("asd/dsa.zip.png", "dsa.zip.png"),
        ("asd\\dsa.zip.png", "dsa.zip.png"),
        ("asd\\foo/bar/dsa.zip.png", "dsa.zip.png"),
        ("asd\\foo/bar/.././dsa-zip_.png", "dsa-zip_.png"),
    ],
)
def test_serializers_filename_field(filename: str, expected: str):
    field = FilenameField()
    assert field.to_internal_value(filename) == expected
