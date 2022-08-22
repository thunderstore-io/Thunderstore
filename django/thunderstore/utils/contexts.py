from contextlib import contextmanager
from tempfile import SpooledTemporaryFile
from typing import IO, Any


@contextmanager
def TemporarySpooledCopy(source_file: IO[Any]):
    """
    Context with a temporary copy of the given file.
    """
    try:
        original_pos = source_file.tell()
        source_file.seek(0)
        temp_file = SpooledTemporaryFile()
        temp_file.write(source_file.read())
        temp_file.seek(0)
        source_file.seek(original_pos)
        yield temp_file
    finally:
        temp_file.close()
