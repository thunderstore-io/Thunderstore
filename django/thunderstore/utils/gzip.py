import gzip
import io


def gzip_compress(data: bytes) -> bytes:
    with io.BytesIO() as buffer:
        with gzip.GzipFile(fileobj=buffer, mode="wb") as gz:
            gz.write(data)
        return buffer.getvalue()


def gzip_decompress(data: bytes) -> bytes:
    with io.BytesIO(data) as buffer:
        with gzip.GzipFile(fileobj=buffer, mode="rb") as gz:
            return gz.read()
