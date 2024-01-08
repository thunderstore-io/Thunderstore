from thunderstore.repository.views.mixins import PackageListingDetailView


class PackageChangelogTabView(PackageListingDetailView):
    tab_name = "changelog"
    template_name = "community/packagelisting_changelog.html"
