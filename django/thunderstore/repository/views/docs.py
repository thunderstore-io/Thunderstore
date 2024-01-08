from django.views.generic import TemplateView

from thunderstore.repository.mixins import CommunityMixin


class PackageDocsView(CommunityMixin, TemplateView):
    template_name = "repository/package_docs.html"
