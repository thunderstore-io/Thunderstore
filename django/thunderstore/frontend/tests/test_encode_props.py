import base64
import json
from typing import Any

import pytest
from django.utils.safestring import SafeString

from thunderstore.frontend.extract_props import decode_props
from thunderstore.frontend.templatetags.encode_props import encode_props


@pytest.mark.parametrize(
    "data",
    [
        {"isDeprecated": True, "canDeprecate": False, "canUndeprecate": True},
        "This is a string, not JSON",
    ],
)
def test_encode_props(data: Any):
    encoded = encode_props(data)
    assert isinstance(encoded, SafeString)
    assert encoded.startswith('"')
    assert encoded.endswith('"')
    decoded = json.loads(base64.b64decode(encoded[1:-1]))
    assert decoded == data
    assert decoded == decode_props(encoded[1:-1])
