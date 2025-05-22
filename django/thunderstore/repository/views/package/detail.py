from django.core.exceptions import PermissionDenied
from django.middleware import csrf
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.decorators.csrf import ensure_csrf_cookie

from thunderstore.community.models import PackageCategory, PackageListing
from thunderstore.core.types import UserType
from thunderstore.core.utils import check_validity
from thunderstore.repository.views.mixins import PackageListingDetailView
from thunderstore.repository.views.package._utils import (
    can_view_listing_admin,
    can_view_package_admin,
    get_package_listing_or_404,
)


class PermissionsChecker:
    def __init__(self, package_listing: PackageListing, user: UserType) -> None:
        self.listing = package_listing
        self.user = user

    @cached_property
    def can_manage(self) -> bool:
        return any(
            (
                self.can_manage_deprecation,
                self.can_manage_categories,
                self.can_unlist,
            )
        )

    @cached_property
    def can_manage_deprecation(self) -> bool:
        return self.listing.package.can_user_manage_deprecation(self.user)

    @cached_property
    def can_manage_categories(self) -> bool:
        return check_validity(
            lambda: self.listing.ensure_update_categories_permission(self.user)
        )

    @cached_property
    def can_deprecate(self) -> bool:
        is_not_deprecated = self.listing.package.is_deprecated is False
        return self.can_manage_deprecation and is_not_deprecated

    @cached_property
    def can_undeprecate(self) -> bool:
        is_deprecated = self.listing.package.is_deprecated is True
        return self.can_manage_deprecation and is_deprecated

    @cached_property
    def can_unlist(self) -> bool:
        return self.user.is_superuser

    @cached_property
    def can_moderate(self) -> bool:
        return self.listing.community.can_user_manage_packages(self.user)

    @cached_property
    def can_view_package_admin_page(self) -> bool:
        return can_view_package_admin(self.user, self.listing.package)

    @cached_property
    def can_view_listing_admin_page(self) -> bool:
        return can_view_listing_admin(self.user, self.listing)

    def get_permissions(self) -> dict:
        return {
            "can_manage": self.can_manage,
            "can_manage_deprecation": self.can_manage_deprecation,
            "can_manage_categories": self.can_manage_categories,
            "can_deprecate": self.can_deprecate,
            "can_undeprecate": self.can_undeprecate,
            "can_unlist": self.can_unlist,
            "can_moderate": self.can_moderate,
            "can_view_package_admin_page": self.can_view_package_admin_page,
            "can_view_listing_admin_page": self.can_view_listing_admin_page,
        }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageDetailView(PackageListingDetailView):
    tab_name = "details"

    @cached_property
    def permissions_checker(self):
        return PermissionsChecker(self.object, self.request.user)

    @cached_property
    def csrf_token(self) -> str:
        return csrf.get_token(self.request)

    def get_review_panel(self):
        if not self.permissions_checker.can_moderate:
            return None
        return {
            "reviewStatus": self.object.review_status,
            "rejectionReason": self.object.rejection_reason,
            "internalNotes": self.object.notes,
            "packageListingId": self.object.pk,
        }

    def get_report_panel(self):
        return {
            "packageListingId": self.object.pk,
            "packageVersionId": self.object.package.latest.pk,
            "csrfToken": self.csrf_token,
            "reasonChoices": [
                {"value": "Spam", "label": "Spam"},
                {"value": "Malware", "label": "Suspected malware"},
                {"value": "Reupload", "label": "Unauthorized reupload"},
                {
                    "value": "CopyrightOrLicense",
                    "label": "Copyright / License issue",
                },
                {"value": "Harassment", "label": "Harassment"},
                {"value": "WrongCommunity", "label": "Wrong community"},
                {"value": "WrongCategories", "label": "Wrong categories"},
                {"value": "Other", "label": "Other"},
            ],
            "descriptionMaxLength": 2048,
        }

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        package_listing = context["object"]
        dependant_count = len(package_listing.package.dependants_list)

        if dependant_count == 1:
            dependants_string = (
                f"{dependant_count} other package depends on this package"
            )
        else:
            dependants_string = (
                f"{dependant_count} other packages depend on this package"
            )

        context["dependants_string"] = dependants_string
        context["show_management_panel"] = self.permissions_checker.can_manage
        context[
            "show_listing_admin_link"
        ] = self.permissions_checker.can_view_listing_admin_page
        context[
            "show_package_admin_link"
        ] = self.permissions_checker.can_view_package_admin_page
        context["show_review_status"] = self.permissions_checker.can_manage
        context["show_internal_notes"] = self.permissions_checker.can_moderate

        def format_category(cat: PackageCategory):
            return {"name": cat.name, "slug": cat.slug}

        context["management_panel_props"] = {
            "isDeprecated": package_listing.package.is_deprecated,
            "canDeprecate": self.permissions_checker.can_deprecate,
            "canUndeprecate": self.permissions_checker.can_undeprecate,
            "canUnlist": self.permissions_checker.can_unlist,
            "canUpdateCategories": self.permissions_checker.can_manage_categories,
            "csrfToken": self.csrf_token,
            "currentCategories": [
                format_category(x) for x in package_listing.categories.all()
            ],
            "availableCategories": [
                format_category(x)
                for x in package_listing.community.package_categories.all()
            ],
            "packageListingId": package_listing.pk,
        }
        context["report_button_props"] = self.get_report_panel()
        context["review_panel_props"] = self.get_review_panel()
        return context

    def post_deprecate(self):
        if not self.permissions_checker.can_deprecate:
            raise PermissionDenied()
        self.object.package.deprecate()

    def post_undeprecate(self):
        if not self.permissions_checker.can_undeprecate:
            raise PermissionDenied()
        self.object.package.undeprecate()

    def post_unlist(self):
        if not self.permissions_checker.can_unlist:
            raise PermissionDenied()
        self.object.package.deactivate()

    def post(self, request, **kwargs):
        self.object = self.get_object()
        if not self.permissions_checker.can_manage:
            raise PermissionDenied()
        if "deprecate" in request.POST:
            self.post_deprecate()
        elif "undeprecate" in request.POST:
            self.post_undeprecate()
        elif "unlist" in request.POST:
            self.post_unlist()
        get_package_listing_or_404.clear_cache_with_args(
            namespace=self.kwargs["owner"],
            name=self.kwargs["name"],
            community=self.community,
        )
        return redirect(self.object)
