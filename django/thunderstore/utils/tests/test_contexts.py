from io import BytesIO
from tempfile import TemporaryFile

from thunderstore.utils.contexts import TemporarySpooledCopy


def test_content_is_copied():
    original_content = b"Lorem ipsum"

    with BytesIO() as original:
        original.write(original_content)

        with TemporarySpooledCopy(original) as tmp:
            tmp_content = tmp.read()

    assert tmp_content == original_content


def test_original_file_is_unaffected():
    position = 123

    with TemporaryFile() as original:
        original.truncate(1023)
        original.seek(position)

        with TemporarySpooledCopy(original) as tmp:
            tmp.seek(999)

        assert not original.closed
        assert original.tell() == position
