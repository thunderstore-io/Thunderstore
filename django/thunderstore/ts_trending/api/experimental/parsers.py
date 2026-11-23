import io
import zlib

from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser

from thunderstore.utils.gzip import gzip_decompress


class GzipJSONParser(JSONParser):
    """
    Parses JSON that may be sent with Content-Encoding: gzip.
    """

    def parse(self, stream, media_type=None, parser_context=None):
        request = parser_context["request"]
        if request.META.get("HTTP_CONTENT_ENCODING") == "gzip":
            try:
                stream = io.BytesIO(gzip_decompress(stream.read()))
            except (OSError, EOFError, zlib.error) as e:
                raise ParseError("Invalid gzip body") from e

        return super().parse(stream, media_type, parser_context)
