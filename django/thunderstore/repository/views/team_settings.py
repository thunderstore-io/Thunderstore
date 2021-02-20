from typing import Optional

from django.contrib import messages
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, FormView, TemplateView

from thunderstore.core.mixins import RequireAuthenticationMixin
from thunderstore.core.utils import capture_exception
from thunderstore.repository.forms import (
    AddUploaderIdentityMemberForm,
    CreateUploaderIdentityForm,
    DisbandUploaderIdentityForm,
    EditUploaderIdentityMemberForm,
    RemoveUploaderIdentityMemberForm,
    UploaderIdentityMemberRole,
)
from thunderstore.repository.models import (
    UploaderIdentity,
    UploaderIdentityMember,
    reverse,
)


class SettingsTeamListView(RequireAuthenticationMixin, TemplateView):
    template_name = "settings/team_list.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Teams"
        context["team_memberships"] = UploaderIdentityMember.objects.filter(
            user=self.request.user
        ).select_related("identity")
        return context


class TeamDetailView(DetailView):
    model = UploaderIdentity
    slug_field = "name"
    slug_url_kwarg = "name"
    context_object_name = "team"
    object: Optional[UploaderIdentity]
    membership: Optional[UploaderIdentityMember]

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect("index")
        self.object = self.get_object()
        if not self.object.can_user_access(self.request.user):
            return redirect("settings.teams")
        self.membership = self.object.get_membership_for_user(self.request.user)
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage_members"] = self.get_object().can_user_manage_members(
            self.request.user
        )
        return context


class UserFormKwargs(FormView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SettingsTeamDetailView(TeamDetailView, UserFormKwargs, FormView):
    template_name = "settings/team_detail.html"

    def get_form_class(self):
        if self.request.POST:
            if "demote" in self.request.POST or "promote" in self.request.POST:
                return EditUploaderIdentityMemberForm
            if "kick" in self.request.POST:
                return RemoveUploaderIdentityMemberForm
            raise SuspiciousOperation("Invalid POST request action")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "demote" in self.request.POST or "promote" in self.request.POST:
            instance = UploaderIdentityMember.objects.filter(
                pk=self.request.POST.get("membership")
            ).first()
            if "membership" not in self.request.POST:
                raise SuspiciousOperation("Invalid action; membership not found")
            kwargs["instance"] = instance
        return kwargs

    def get_form(self, *args, **kwargs):
        if self.request.POST:
            return super().get_form(*args, **kwargs)
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Team {self.get_object().name} Members"
        return context

    def form_invalid(self, form):
        messages.error(
            self.request, "There was a problem performing the requested action"
        )
        capture_exception(ValidationError(form.errors))
        return super().form_invalid(form)

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Action performed successfully")
        return redirect(self.object.settings_url)


class SettingsTeamAddMemberView(TeamDetailView, UserFormKwargs, FormView):
    template_name = "settings/team_add_member.html"
    form_class = AddUploaderIdentityMemberForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Add member to Team {self.object.name}"
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Member added successfully")
        return redirect(self.object.settings_url)


class SettingsTeamCreateView(RequireAuthenticationMixin, UserFormKwargs, CreateView):
    model = UploaderIdentity
    form_class = CreateUploaderIdentityForm
    template_name = "settings/team_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create Team"
        return context

    @transaction.atomic
    def form_valid(self, form):
        instance = form.save()
        return redirect(instance.settings_url)


class SettingsTeamDisbandView(TeamDetailView, UserFormKwargs, FormView):
    model = UploaderIdentity
    form_class = DisbandUploaderIdentityForm
    template_name = "settings/team_disband.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Disband Team"
        context["can_disband"] = not self.object.owned_packages.exists()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(dict(instance=self.object))
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        form.save()
        return redirect(reverse("settings.teams"))


class SettingsTeamLeaveView(TeamDetailView, UserFormKwargs, FormView):
    model = UploaderIdentity
    form_class = RemoveUploaderIdentityMemberForm
    template_name = "settings/team_leave.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Leave Team"
        context["membership"] = self.membership
        context["can_leave"] = (
            self.object.members.real_users()
            .filter(role=UploaderIdentityMemberRole.owner)
            .count()
            > 1
        )
        return context

    def form_invalid(self, form):
        messages.error(
            self.request, "There was a problem performing the requested action"
        )
        capture_exception(ValidationError(form.errors))
        return super().form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        form.save()
        return redirect(reverse("settings.teams"))
