import shutil
from contextlib import contextmanager
from tempfile import SpooledTemporaryFile
from typing import IO, Any

# Copies larger than this are written to disk instead of being held in memory.
SPOOLED_COPY_MAX_MEMORY_SIZE = 16 * 1024 * 1024


@contextmanager
def TemporarySpooledCopy(source_file: IO[Any]):
    """
    Context with a temporary copy of the given file.
    """
    try:
        original_pos = source_file.tell()
        source_file.seek(0)
        temp_file = SpooledTemporaryFile(max_size=SPOOLED_COPY_MAX_MEMORY_SIZE)
        shutil.copyfileobj(source_file, temp_file)
        temp_file.seek(0)
        source_file.seek(original_pos)
        yield temp_file
    finally:
        temp_file.close()
