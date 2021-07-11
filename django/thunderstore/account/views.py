from thunderstore.repository.models.package import Package
from thunderstore.repository.models.uploader_identity import UploaderIdentity
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.http import HttpResponse


class ProfileView(TemplateView):
    template_name="profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        username = kwargs["user"]
        context['user'] = get_object_or_404(UploaderIdentity, name=username)
        userpackages = sorted(Package.objects.filter(owner__name=username).all(), key=lambda x: x.downloads)
        context['popular_packages'] = userpackages[:4]
        context['package_count'] = len(userpackages)
        context['total_downloads'] = sum(package.downloads for package in userpackages)
        context['total_likes'] = sum(package.rating_score for package in userpackages)
        return context