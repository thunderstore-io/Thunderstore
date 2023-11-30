import os
from typing import Any

import pytest

from thunderstore.frontend.extract_props import (
    decode_props,
    enumerate_scripts,
    extract_props_from_html,
)


def _load_test_data(path: str) -> str:
    full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    with open(full_path, "r") as f:
        return f.read()


@pytest.mark.parametrize(
    ("encoded", "expected"),
    (
        (
            "eyJpc0RlcHJlY2F0ZWQiOiB0cnVlLCAiY2FuRGVwcmVjYXRlIjogZmFsc2UsICJjYW5VbmRlcHJlY2F0ZSI6IHRydWV9",
            {"isDeprecated": True, "canDeprecate": False, "canUndeprecate": True},
        ),
        (
            "ImhlbGxvIg==",
            "hello",
        ),
    ),
)
def test_decode_props(encoded: str, expected: Any) -> None:
    assert decode_props(encoded) == expected


def test_enumerate_scripts() -> None:
    test_html = _load_test_data("data/scripts.html")
    scripts = list(enumerate_scripts(test_html))
    expected = [
        'const test = "test";',
        """
window.ts.PackageManagementPanel(
    document.getElementById("package-management-panel"),
    "eyJpc0RlcHJlY2F0ZWQiOiBmYWxzZSwgImNhbkRlcHJlY2F0ZSI6IHRydWUsICJjYW5VbmRlcHJlY2F0ZSI6IGZhbHNlfQ=="
);
""",
    ]

    assert len(scripts) == len(expected)
    for found, expected in zip(scripts, expected):
        assert found.strip() == expected.strip()


def test_extract_props_from_html() -> None:
    test_html = _load_test_data("data/scripts.html")
    expected = {"isDeprecated": False, "canDeprecate": True, "canUndeprecate": False}
    props = extract_props_from_html(
        test_html, "PackageManagementPanel", "package-management-panel"
    )
    assert props == expected
    assert extract_props_from_html(test_html, "PackageManagementPanel", "wrong") is None
    assert (
        extract_props_from_html(test_html, "wrong", "package-management-panel") is None
    )
