from typing import Optional

from django.contrib import messages
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.generic import CreateView, DetailView, FormView, TemplateView

from thunderstore.account.forms import (
    CreateServiceAccountForm,
    DeleteServiceAccountForm,
)
from thunderstore.core.mixins import RequireAuthenticationMixin
from thunderstore.core.utils import capture_exception
from thunderstore.repository.forms import (
    AddTeamMemberForm,
    CreateTeamForm,
    DisbandTeamForm,
    EditTeamMemberForm,
    RemoveTeamMemberForm,
    TeamMemberRole,
)
from thunderstore.repository.models import Team, TeamMember, reverse


class SettingsTeamListView(RequireAuthenticationMixin, TemplateView):
    template_name = "settings/team_list.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Teams"
        context["team_memberships"] = TeamMember.objects.filter(
            user=self.request.user
        ).select_related("team")
        return context


class TeamDetailView(DetailView):
    model = Team
    slug_field = "name"
    slug_url_kwarg = "name"
    context_object_name = "team"
    object: Optional[Team]
    membership: Optional[TeamMember]

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
                return EditTeamMemberForm
            if "kick" in self.request.POST:
                return RemoveTeamMemberForm
            raise SuspiciousOperation("Invalid POST request action")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "demote" in self.request.POST or "promote" in self.request.POST:
            instance = TeamMember.objects.filter(
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
    form_class = AddTeamMemberForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Add member to Team {self.object.name}"
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Member added successfully")
        return redirect(self.object.settings_url)


class SettingsTeamCreateView(RequireAuthenticationMixin, UserFormKwargs, CreateView):
    model = Team
    form_class = CreateTeamForm
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
    model = Team
    form_class = DisbandTeamForm
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
    model = Team
    form_class = RemoveTeamMemberForm
    template_name = "settings/team_leave.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Leave Team"
        context["membership"] = self.membership
        context["can_leave"] = (
            self.object.members.real_users().filter(role=TeamMemberRole.owner).count()
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


class SettingsTeamServiceAccountView(TeamDetailView, UserFormKwargs, FormView):
    template_name = "settings/team_service_account.html"

    def get_form_class(self):
        if self.request.POST:
            if "remove" in self.request.POST:
                return DeleteServiceAccountForm
            raise SuspiciousOperation("Invalid POST request action")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "remove" in self.request.POST and "service_account" not in self.request.POST:
            raise SuspiciousOperation("Invalid action; service_account not found")
        return kwargs

    def get_form(self, *args, **kwargs):
        if self.request.POST:
            return super().get_form(*args, **kwargs)
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Team {self.get_object().name} service accounts"
        team = self.get_object()
        context["can_create"] = team.can_user_create_service_accounts(self.request.user)
        context["can_delete"] = team.can_user_delete_service_accounts(self.request.user)
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
        return redirect(self.object.service_accounts_url)


class SettingsTeamAddServiceAccountView(TeamDetailView, UserFormKwargs, FormView):
    template_name = "settings/team_add_service_account.html"
    form_class = CreateServiceAccountForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Add service account for Team {self.object.name}"
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Service account added successfully")
        context = super().get_context_data()
        context["api_token"] = form.api_token
        context["nickname"] = form.cleaned_data["nickname"]
        return render(self.request, self.template_name, context)
