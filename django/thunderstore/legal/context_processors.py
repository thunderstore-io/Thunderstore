from django_contracts.models import LegalContract
from django_contracts.models.publishable import PublishStatus


def legal_contracts(request):
    return {
        "legal_contracts": LegalContract.objects.filter(
            publish_status=PublishStatus.PUBLISHED
        )
        .exclude(latest=None)
        .order_by("-title")
    }
