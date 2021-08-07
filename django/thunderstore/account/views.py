from django.shortcuts import get_object_or_404
from thunderstore.repository.models.package import Package
from django.views.generic.base import TemplateView
from django.contrib.auth.models import User
import hashlib



class ProfileView(TemplateView):
    template_name="profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the user
        username = kwargs["user"]
        context['user'] = get_object_or_404(User, username=username)
        context['social_providers'] = context['user'].social_auth.all()

        # Get the packages from this user and total up the stats
        userpackages = sorted(Package.objects.filter(owner__name=username).all(), key=lambda x: x.downloads)
        context['popular_packages'] = userpackages[:4]
        context['package_count'] = len(userpackages)
        context['total_downloads'] = sum(package.downloads for package in userpackages)
        context['total_likes'] = sum(package.rating_score for package in userpackages)
        context['email_hash'] = hashlib.md5(context['user'].email.lower().encode()).hexdigest()

        return context
