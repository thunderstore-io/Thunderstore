from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from thunderstore.repository.views.mixins import PackageListingDetailView


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageDetailView(PackageListingDetailView):
    tab_name = "details"

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

        return context
