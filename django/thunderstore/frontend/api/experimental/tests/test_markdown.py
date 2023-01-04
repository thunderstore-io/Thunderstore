import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.repository.validation.markdown import MAX_MARKDOWN_SIZE

MARKDOWN_UNRENDERED = """
# Test markdown

this is a description
""".strip()

MARKDOWN_RENDERED = """<h1>Test markdown</h1>
<p>this is a description</p>
"""


@pytest.mark.django_db
def test_api_experimental_render_markdown_success(api_client: APIClient) -> None:
    response = api_client.post(
        reverse("api:experimental:frontend.render-markdown"),
        json.dumps(
            {
                "markdown": MARKDOWN_UNRENDERED,
            },
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json() == {"html": MARKDOWN_RENDERED}


@pytest.mark.django_db
def test_api_experimental_render_markdown_too_long(api_client: APIClient) -> None:
    response = api_client.post(
        reverse("api:experimental:frontend.render-markdown"),
        json.dumps(
            {
                "markdown": "a" * (MAX_MARKDOWN_SIZE + 1),
            },
        ),
        content_type="application/json",
    )
    print(response.content)
    assert response.status_code == 400
    assert response.json() == {
        "markdown": [
            f"Ensure this field has no more than {MAX_MARKDOWN_SIZE} characters."
        ],
    }
