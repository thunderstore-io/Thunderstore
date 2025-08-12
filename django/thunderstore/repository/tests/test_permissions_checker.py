from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("can_manage_deprecation, can_manage_categories, can_unlist, expected_result"),
    [
        (True, True, True, True),
        (True, True, False, True),
        (True, False, True, True),
        (True, False, False, True),
        (False, True, True, True),
        (False, True, False, True),
        (False, False, True, True),
        (False, False, False, False),
    ],
)
def test_can_manage(
    permissions_checker,
    can_manage_deprecation,
    can_manage_categories,
    can_unlist,
    expected_result,
):
    permissions_checker.can_manage_deprecation = can_manage_deprecation
    permissions_checker.can_manage_categories = can_manage_categories
    permissions_checker.can_unlist = can_unlist

    assert permissions_checker.can_manage == expected_result


@pytest.mark.django_db
@pytest.mark.parametrize("return_val", (True, False))
@patch("thunderstore.repository.models.package.Package.can_user_manage_deprecation")
def test_can_manage_deprecation(
    mock_can_user_manage_deprecation,
    return_val,
    permissions_checker,
):
    mock_can_user_manage_deprecation.return_value = return_val
    assert permissions_checker.can_manage_deprecation == return_val


@pytest.mark.django_db
@pytest.mark.parametrize("return_val", ([], ["Some error"]))
@patch(
    "thunderstore.community.models.PackageListing.validate_update_categories_permissions"
)
def test_can_manage_categories(
    mock_ensure_update_categories_permission, return_val, permissions_checker
):
    expected_response = len(return_val) == 0
    mock_ensure_update_categories_permission.return_value = return_val
    assert permissions_checker.can_manage_categories == expected_response


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("is_deprecated", "can_manage_deprecation", "expected_result"),
    [
        (True, True, False),
        (True, False, False),
        (False, True, True),
        (False, False, False),
    ],
)
def test_can_deprecate(
    is_deprecated,
    can_manage_deprecation,
    expected_result,
    permissions_checker,
):
    permissions_checker.listing.package.is_deprecated = is_deprecated
    permissions_checker.can_manage_deprecation = can_manage_deprecation
    assert permissions_checker.can_deprecate == expected_result


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("is_deprecated", "can_manage_deprecation", "expected_result"),
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_can_undeprecate(
    permissions_checker, is_deprecated, can_manage_deprecation, expected_result
):
    permissions_checker.listing.package.is_deprecated = is_deprecated
    permissions_checker.can_manage_deprecation = can_manage_deprecation
    assert permissions_checker.can_undeprecate == expected_result


@pytest.mark.django_db
@pytest.mark.parametrize("is_superuser", (True, False))
def test_can_unlist(permissions_checker, is_superuser):
    permissions_checker.user.is_superuser = is_superuser
    assert permissions_checker.can_unlist == is_superuser


@pytest.mark.django_db
@pytest.mark.parametrize("return_val", (True, False))
@patch(
    "thunderstore.community.models.community.Community."
    "ensure_user_can_moderate_packages"
)
def test_can_moderate(
    mock_ensure_can_moderate_packages, return_val, permissions_checker
):
    if return_val is True:
        mock_ensure_can_moderate_packages.return_value = return_val
    else:
        mock_ensure_can_moderate_packages.side_effect = ValidationError("Failed")
    assert permissions_checker.can_moderate == return_val


@pytest.mark.django_db
@pytest.mark.parametrize("return_val", (True, False))
@patch("thunderstore.repository.views.package.detail.can_view_package_admin")
def test_can_view_package_admin_page(mock_func, return_val, permissions_checker):
    mock_func.return_value = return_val
    assert permissions_checker.can_view_package_admin_page == return_val


@pytest.mark.django_db
@pytest.mark.parametrize("return_val", (True, False))
@patch("thunderstore.repository.views.package.detail.can_view_listing_admin")
def test_can_view_listing_admin_page(mock_func, return_val, permissions_checker):
    mock_func.return_value = return_val
    assert permissions_checker.can_view_listing_admin_page == return_val


@pytest.mark.django_db
def test_get_permissions(permissions_checker):
    permissions = permissions_checker.get_permissions()
    expected_permissions = {
        "can_manage": permissions_checker.can_manage,
        "can_manage_deprecation": permissions_checker.can_manage_deprecation,
        "can_manage_categories": permissions_checker.can_manage_categories,
        "can_deprecate": permissions_checker.can_deprecate,
        "can_undeprecate": permissions_checker.can_undeprecate,
        "can_unlist": permissions_checker.can_unlist,
        "can_moderate": permissions_checker.can_moderate,
        "can_view_package_admin_page": permissions_checker.can_view_package_admin_page,
        "can_view_listing_admin_page": permissions_checker.can_view_listing_admin_page,
    }
    assert permissions == expected_permissions
