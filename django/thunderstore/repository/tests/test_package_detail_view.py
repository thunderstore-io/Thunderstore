from unittest.mock import PropertyMock, patch

import pytest
from django.urls import reverse

PERMISSION_KEYS = [
    "show_management_panel",
    "show_listing_admin_link",
    "show_package_admin_link",
    "show_review_status",
    "show_internal_notes",
    "review_panel_props",
]


PERMISSION_KEYS_TEST_PARAMETERS = [
    (PERMISSION_KEYS[0], "can_manage", True),
    (PERMISSION_KEYS[0], "can_manage", False),
    (PERMISSION_KEYS[1], "can_view_listing_admin_page", True),
    (PERMISSION_KEYS[1], "can_view_listing_admin_page", False),
    (PERMISSION_KEYS[2], "can_view_package_admin_page", True),
    (PERMISSION_KEYS[2], "can_view_package_admin_page", False),
    (PERMISSION_KEYS[3], "can_manage", True),
    (PERMISSION_KEYS[3], "can_manage", False),
    (PERMISSION_KEYS[4], "can_moderate", True),
    (PERMISSION_KEYS[4], "can_moderate", False),
]


REVIEW_PANEL_PROPS_KEYS = [
    "reviewStatus",
    "rejectionReason",
    "internalNotes",
    "packageListingId",
]


REVIEW_PANEL_PROPS_TEST_PARAMETERS = [
    ("can_moderate", False, None),
    ("can_moderate", True, REVIEW_PANEL_PROPS_KEYS),
]


MANAGEMENT_PANEL_PROPS_KEYS = [
    "canDeprecate",
    "canUndeprecate",
    "canUnlist",
    "canUpdateCategories",
]


MANAGEMENT_PANEL_PROPS_TEST_PARAMETERS = [
    (MANAGEMENT_PANEL_PROPS_KEYS[0], "can_deprecate", True),
    (MANAGEMENT_PANEL_PROPS_KEYS[0], "can_deprecate", False),
    (MANAGEMENT_PANEL_PROPS_KEYS[1], "can_undeprecate", True),
    (MANAGEMENT_PANEL_PROPS_KEYS[1], "can_undeprecate", False),
    (MANAGEMENT_PANEL_PROPS_KEYS[2], "can_unlist", True),
    (MANAGEMENT_PANEL_PROPS_KEYS[2], "can_unlist", False),
    (MANAGEMENT_PANEL_PROPS_KEYS[3], "can_manage_categories", True),
    (MANAGEMENT_PANEL_PROPS_KEYS[3], "can_manage_categories", False),
]


def get_package_detail_view_url(owner: str, name: str):
    # Note: this is the legacy URL
    return reverse("old_urls:packages.detail", kwargs={"owner": owner, "name": name})


@pytest.mark.django_db
def test_package_detail_view_permission_keys_in_context(
    client, active_package_listing, community_site
):
    """
    Test that the expected permission keys are present in the context.
    """

    owner = active_package_listing.package.owner
    package = active_package_listing.package
    url = get_package_detail_view_url(owner=owner.name, name=package.name)

    response = client.get(url, HTTP_HOST=community_site.site.domain)
    context = response.context[0]
    management_panel_props = context.get("management_panel_props", {})

    assert response.status_code == 200

    for key in PERMISSION_KEYS:
        assert key in context

    for key in MANAGEMENT_PANEL_PROPS_KEYS:
        assert key in management_panel_props


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("permission_key", "permissions_checker_function", "return_value"),
    PERMISSION_KEYS_TEST_PARAMETERS,
)
def test_package_detail_view_permission_keys_test_values(
    permission_key,
    permissions_checker_function,
    return_value,
    client,
    active_package_listing,
    community_site,
):
    """
    Test that the permission keys in the context have the expected values. The values
    are determined by the return value of the permissions checker function.
    """

    owner = active_package_listing.package.owner
    package = active_package_listing.package
    url = get_package_detail_view_url(owner=owner.name, name=package.name)

    path = (
        f"thunderstore.repository.views.package.detail."
        f"PermissionsChecker.{permissions_checker_function}"
    )
    with patch(path, new_callable=PropertyMock) as mock_permissions_checker_function:
        mock_permissions_checker_function.return_value = return_value
        response = client.get(url, HTTP_HOST=community_site.site.domain)

    context = response.context[0]
    assert context[permission_key] == return_value


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("permissions_checker_function", "return_value", "expected_keys"),
    REVIEW_PANEL_PROPS_TEST_PARAMETERS,
)
def test_package_detail_view_review_panel_props_keys(
    permissions_checker_function,
    return_value,
    expected_keys,
    client,
    active_package_listing,
    community_site,
):
    """
    Test that the review panel props are present with the correct values in the context.
    The review panel props are either None or a dictionary with the expected keys.
    """

    owner = active_package_listing.package.owner
    package = active_package_listing.package
    url = get_package_detail_view_url(owner=owner.name, name=package.name)

    path = (
        f"thunderstore.repository.views.package.detail."
        f"PermissionsChecker.{permissions_checker_function}"
    )
    with patch(path, new_callable=PropertyMock) as mock_permissions_checker_function:
        mock_permissions_checker_function.return_value = return_value
        response = client.get(url, HTTP_HOST=community_site.site.domain)

    context = response.context[0]
    review_panel_props = context["review_panel_props"]

    if return_value:
        for key in expected_keys:
            assert key in review_panel_props
    else:
        assert review_panel_props is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("management_panel_prop_key", "permissions_checker_function", "return_value"),
    MANAGEMENT_PANEL_PROPS_TEST_PARAMETERS,
)
def test_package_detail_view_management_panel_props(
    management_panel_prop_key,
    permissions_checker_function,
    return_value,
    client,
    active_package_listing,
    community_site,
):
    """
    Test that the management panel props are present with the correct values in the
    context. The values are determined by the return value of the permissions checker
    properties.
    """

    owner = active_package_listing.package.owner
    package = active_package_listing.package
    url = get_package_detail_view_url(owner=owner.name, name=package.name)

    path = (
        f"thunderstore.repository.views.package.detail."
        f"PermissionsChecker.{permissions_checker_function}"
    )
    with patch(path, new_callable=PropertyMock) as mock_permissions_checker_function:
        mock_permissions_checker_function.return_value = return_value
        response = client.get(url, HTTP_HOST=community_site.site.domain)

    context = response.context[0]
    management_panel_props = context["management_panel_props"]
    assert management_panel_props[management_panel_prop_key] == return_value
