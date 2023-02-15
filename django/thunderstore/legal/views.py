from typing import Any, Dict

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from django_contracts.models.contract import LegalContract, LegalContractVersion
from django_contracts.models.publishable import PublishStatus


class LegalContractBaseview(TemplateView):
    template_name = "contracts/contract.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        version = self.get_legal_contract_version()
        context["contract"] = version.contract
        context["version"] = version
        return context

    def get_legal_contract_version(self) -> LegalContractVersion:
        raise NotImplementedError()


class LegalContractView(LegalContractBaseview):
    def get_legal_contract_version(self) -> LegalContractVersion:
        contract = (
            LegalContract.objects.filter(
                slug=self.kwargs.get("contract"),
                publish_status=PublishStatus.PUBLISHED,
            )
            .select_related("latest")
            .first()
        )
        if contract and (version := contract.latest) is not None:
            return version
        raise Http404()


class LegalContractVersionView(LegalContractBaseview):
    def get_legal_contract_version(self) -> LegalContractVersion:
        contract = get_object_or_404(
            LegalContractVersion,
            pk=self.kwargs.get("version"),
            contract__slug=self.kwargs.get("contract"),
        )
        is_public = (
            contract.publish_status == PublishStatus.PUBLISHED
            or contract.contract.latest == contract
        )
        if is_public or self.request.user.is_staff:
            return contract
        raise Http404()


class LegalContractHistoryView(TemplateView):
    template_name = "contracts/contract_history.html"

    @property
    def visible_statuses(self):
        visible_statuses = [PublishStatus.PUBLISHED]
        if self.request.user.is_staff:
            visible_statuses.append(PublishStatus.DRAFT)
        return visible_statuses

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["contract"] = get_object_or_404(
            LegalContract,
            slug=self.kwargs.get("contract"),
            publish_status__in=self.visible_statuses,
        )
        context["versions"] = LegalContractVersion.objects.filter(
            contract__slug=self.kwargs.get("contract"),
            publish_status__in=self.visible_statuses,
        ).order_by(
            "-datetime_published",
        )
        return context
