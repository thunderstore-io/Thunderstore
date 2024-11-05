from io import BytesIO
from zipfile import ZipFile

import pytest

from thunderstore.repository.validation.zip import check_unsafe_paths, check_zero_offset


@pytest.mark.parametrize(
    ("path", "expected"),
    (("foo.txt", False), ("foo/../foo.txt", True), ("../foo.txt", True)),
)
def test_zip_check_unsafe_paths(path: str, expected: bool):
    buffer = BytesIO()

    with ZipFile(buffer, "w") as zf:
        zf.writestr(path, "foo")

    with ZipFile(buffer, "r") as zf:
        assert check_unsafe_paths(zf.infolist()) is expected


@pytest.mark.parametrize(
    ("bogus_bytes", "expected"), ((0, True), (1000, False), (1, False))
)
def test_zip_check_zero_offset(bogus_bytes: int, expected: bool):
    buffer = BytesIO(b"a" * bogus_bytes)

    with ZipFile(buffer, "a") as zf:
        zf.writestr("bar.txt", "foo")

    with ZipFile(buffer, "r") as zf:
        assert check_zero_offset(zf.infolist()) is expected
