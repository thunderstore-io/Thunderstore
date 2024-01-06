from thunderstore.repository.views.mixins import PackageListingDetailView


class PackageVersionsTabView(PackageListingDetailView):
    tab_name = "versions"
    template_name = "community/packagelisting_versions.html"
