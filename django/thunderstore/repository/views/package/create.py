from django.conf import settings
from django.db import models, transaction
from django.db.models import ExpressionWrapper, Q
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import CreateView, TemplateView

from thunderstore.community.models import Community, PackageListing
from thunderstore.frontend.api.experimental.serializers.views import CommunitySerializer
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.models import PackageVersion, Team
from thunderstore.repository.package_upload import PackageUploadForm


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageCreateView(CommunityMixin, TemplateView):
    template_name = "repository/package_create.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        serializer = CommunitySerializer(self.community)
        context["upload_page_props"] = {
            "currentCommunity": serializer.data,
            "useAsyncFlow": settings.USE_ASYNC_PACKAGE_SUBMISSION_FLOW,
        }
        return context

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect("index")
        return super().dispatch(*args, **kwargs)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageCreateOldView(CommunityMixin, CreateView):
    model = PackageVersion
    form_class = PackageUploadForm
    template_name = "repository/package_create_old.html"

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect("index")
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selectable_communities"] = (
            Community.objects.filter(
                Q(is_listed=True) | Q(pk=self.community.pk),
            )
            .annotate(
                is_current_community=ExpressionWrapper(
                    Q(pk=self.community.pk), output_field=models.BooleanField()
                )
            )
            .order_by("-is_current_community", "name")
        )
        context["current_community"] = self.community
        return context

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs["user"] = self.request.user
        kwargs["community"] = self.community
        kwargs["initial"] = {
            "team": Team.get_default_for_user(self.request.user),
            "communities": [],
        }
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        instance: PackageVersion = form.save()
        listing = PackageListing.objects.filter(
            package=instance.package,
            community__in=form.cleaned_data.get("communities"),
        ).first()
        # TODO: Remove reliance on instance.get_absolute_url()
        redirect_url = (
            listing.get_full_url() if listing else instance.get_absolute_url()
        )
        return redirect(redirect_url)
