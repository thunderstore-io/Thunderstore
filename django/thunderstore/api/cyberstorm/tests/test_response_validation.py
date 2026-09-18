import pytest
from django.http import HttpResponse
from jsonschema import RefResolver

from thunderstore.api.cyberstorm.tests.utils import validate_response_against_schema


@pytest.mark.parametrize(
    ("content_type", "response_schema", "expected_error"),
    [
        ("text/markdown; charset=utf-8", {"type": "string"}, None),
        ("text/html", {"type": "string"}, "Unexpected content type"),
        ("text/markdown", {"type": "object"}, "Validation error"),
    ],
)
def test_text_response_contract(content_type, response_schema, expected_error):
    schema = {
        "paths": {
            "/download/": {
                "get": {
                    "produces": ["text/markdown"],
                    "responses": {"200": {"schema": response_schema}},
                }
            }
        }
    }
    response = HttpResponse("# Markdown", content_type=content_type)

    errors = validate_response_against_schema(
        response, "/download/", "GET", schema, RefResolver.from_schema(schema)
    )

    if expected_error:
        assert len(errors) == 1
        assert expected_error in errors[0]
    else:
        assert errors == []
