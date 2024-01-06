from typing import Optional

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.middleware import csrf
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import DetailView

from thunderstore.community.models import PackageCategory, PackageListing
from thunderstore.core.utils import check_validity
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.views.mixins import PackageTabsMixin
from thunderstore.repository.views.package._utils import (
    can_view_listing_admin,
    can_view_package_admin,
    get_package_listing_or_404,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageDetailView(CommunityMixin, PackageTabsMixin, DetailView):
    model = PackageListing
    object: Optional[PackageListing]

    def get_object(self, *args, **kwargs) -> PackageListing:
        listing = get_package_listing_or_404(
            namespace=self.kwargs["owner"],
            name=self.kwargs["name"],
            community=self.community,
        )
        if not listing.can_be_viewed_by_user(self.request.user):
            raise Http404("Package is waiting for approval or has been rejected")
        return listing

    @cached_property
    def can_manage(self):
        return any(
            (
                self.can_manage_deprecation,
                self.can_manage_categories,
                self.can_unlist,
            )
        )

    @cached_property
    def can_manage_deprecation(self):
        return self.object.package.can_user_manage_deprecation(self.request.user)

    @cached_property
    def can_manage_categories(self) -> bool:
        return check_validity(
            lambda: self.object.ensure_update_categories_permission(self.request.user)
        )

    @cached_property
    def can_deprecate(self):
        return (
            self.can_manage_deprecation and self.object.package.is_deprecated is False
        )

    @cached_property
    def can_undeprecate(self):
        return self.can_manage_deprecation and self.object.package.is_deprecated is True

    @cached_property
    def can_unlist(self):
        return self.request.user.is_superuser

    @cached_property
    def can_moderate(self) -> bool:
        return self.object.community.can_user_manage_packages(self.request.user)

    def get_review_panel(self):
        if not self.can_moderate:
            return None
        return {
            "reviewStatus": self.object.review_status,
            "rejectionReason": self.object.rejection_reason,
            "internalNotes": self.object.notes,
            "packageListingId": self.object.pk,
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
        context["show_management_panel"] = self.can_manage
        context["show_listing_admin_link"] = can_view_listing_admin(
            self.request.user, package_listing
        )
        context["show_package_admin_link"] = can_view_package_admin(
            self.request.user, package_listing.package
        )
        context["show_review_status"] = self.can_manage
        context["show_internal_notes"] = self.can_moderate

        def format_category(cat: PackageCategory):
            return {"name": cat.name, "slug": cat.slug}

        context["management_panel_props"] = {
            "isDeprecated": package_listing.package.is_deprecated,
            "canDeprecate": self.can_deprecate,
            "canUndeprecate": self.can_undeprecate,
            "canUnlist": self.can_unlist,
            "canUpdateCategories": self.can_manage_categories,
            "csrfToken": csrf.get_token(self.request),
            "currentCategories": [
                format_category(x) for x in package_listing.categories.all()
            ],
            "availableCategories": [
                format_category(x)
                for x in package_listing.community.package_categories.all()
            ],
            "packageListingId": package_listing.pk,
        }
        context["review_panel_props"] = self.get_review_panel()
        context.update(
            **self.get_tab_context(self.request.user, package_listing, "details")
        )
        return context

    def post_deprecate(self):
        if not self.can_deprecate:
            raise PermissionDenied()
        self.object.package.deprecate()

    def post_undeprecate(self):
        if not self.can_undeprecate:
            raise PermissionDenied()
        self.object.package.undeprecate()

    def post_unlist(self):
        if not self.can_unlist:
            raise PermissionDenied()
        self.object.package.deactivate()

    def post(self, request, **kwargs):
        self.object = self.get_object()
        if not self.can_manage:
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
