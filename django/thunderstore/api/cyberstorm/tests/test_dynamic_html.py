import pytest
from rest_framework.test import APIClient

from thunderstore.frontend.models import DynamicHTML, DynamicPlacement


@pytest.mark.django_db
def test_get_dynamic_html__returns_not_found__when_no_active(
    api_client: APIClient,
) -> None:
    DynamicHTML.objects.create(
        name="dynamic_placement_1",
        placement=DynamicPlacement.cyberstorm_header,
        content="<title>DYNAMIC HTML TITLE</title>",
        ordering=0,
        is_active=False,
    )
    DynamicHTML.objects.create(
        name="dynamic_placement_2",
        placement=DynamicPlacement.cyberstorm_header,
        content='<script>console.log("DYNAMIC HTML SCRIPT")</script>',
        ordering=1,
        is_active=False,
    )

    response = api_client.get(
        f"/api/cyberstorm/dynamichtml/{DynamicPlacement.cyberstorm_header}/",
    )
    actual = response.json()

    print(actual)
    assert actual["detail"] == "Not found."


@pytest.mark.django_db
def test_get_dynamic_html__returns_not_found__when_bad_placement_arg(
    api_client: APIClient,
) -> None:
    DynamicHTML.objects.create(
        name="dynamic_placement_1",
        placement=DynamicPlacement.cyberstorm_header,
        content="<title>DYNAMIC HTML TITLE</title>",
        ordering=0,
    )

    response = api_client.get(
        f"/api/cyberstorm/dynamichtml/{DynamicPlacement.cyberstorm_header + 'bad'}/",
    )
    actual = response.json()

    assert actual["detail"] == "Not found."


@pytest.mark.django_db
def test_get_dynamic_html__returns_not_found__when_placement_arg_doesnt_start_with_cyberstorm(
    api_client: APIClient,
) -> None:
    DynamicHTML.objects.create(
        name="dynamic_placement_1",
        placement=DynamicPlacement.cyberstorm_header,
        content="<title>DYNAMIC HTML TITLE</title>",
        ordering=0,
    )

    response = api_client.get(
        f"/api/cyberstorm/dynamichtml/{DynamicPlacement.cyberstorm_header[len('cyberstorm_'):]}/",
    )
    actual = response.json()

    assert actual["detail"] == "Not found."


@pytest.mark.django_db
def test_get_dynamic_html__returns_correct_object__when_multiple(
    api_client: APIClient,
) -> None:
    DynamicHTML.objects.create(
        name="dynamic_placement_1",
        placement=DynamicPlacement.cyberstorm_header,
        content="<title>DYNAMIC HTML TITLE</title>",
        ordering=0,
        is_active=False,
    )
    DynamicHTML.objects.create(
        name="dynamic_placement_2",
        placement=DynamicPlacement.cyberstorm_header,
        content='<script>console.log("DYNAMIC HTML SCRIPT")</script>',
        ordering=1,
    )

    response = api_client.get(
        f"/api/cyberstorm/dynamichtml/{DynamicPlacement.cyberstorm_header}/",
    )
    actual = response.json()

    assert (
        actual["dynamic_htmls"][0]
        == "\\u003Cscript\\u003Econsole.log(\\u0022DYNAMIC HTML SCRIPT\\u0022)\\u003C/script\\u003E"
    )


@pytest.mark.django_db
def test_get_dynamic_html__returns_multiple(api_client: APIClient) -> None:
    DynamicHTML.objects.create(
        name="dynamic_placement_1",
        placement=DynamicPlacement.cyberstorm_header,
        content="<title>DYNAMIC HTML TITLE</title>",
        ordering=1,
    )
    DynamicHTML.objects.create(
        name="dynamic_placement_2",
        placement=DynamicPlacement.cyberstorm_header,
        content='<script>console.log("DYNAMIC HTML SCRIPT")</script>',
        ordering=0,
    )

    response = api_client.get(
        f"/api/cyberstorm/dynamichtml/{DynamicPlacement.cyberstorm_header}/",
    )
    actual = response.json()

    assert (
        actual["dynamic_htmls"][0]
        == "\\u003Cscript\\u003Econsole.log(\\u0022DYNAMIC HTML SCRIPT\\u0022)\\u003C/script\\u003E"
    )
    assert (
        actual["dynamic_htmls"][1]
        == "\\u003Ctitle\\u003EDYNAMIC HTML TITLE\\u003C/title\\u003E"
    )
