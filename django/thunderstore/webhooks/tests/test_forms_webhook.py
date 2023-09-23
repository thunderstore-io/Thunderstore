from typing import Dict

import pytest
from django.db.models.sql.where import NothingNode
from django.forms import model_to_dict

from thunderstore.community.models import Community, PackageCategory
from thunderstore.webhooks.forms import WebhookAdminForm, WebhookForm
from thunderstore.webhooks.models import Webhook, WebhookType


def _create_category(community: Community) -> PackageCategory:
    return PackageCategory.objects.create(
        community=community,
        name="Test category",
        slug="test-category",
    )


def _form_from_instance(webhook: Webhook, data: Dict[str, any]) -> WebhookForm:
    return WebhookForm(
        instance=webhook,
        data={
            **(model_to_dict(webhook)),
            **data,
        },
    )


@pytest.mark.django_db
@pytest.mark.parametrize("field_name", ("require_categories", "exclude_categories"))
def test_webhook_form_modify_categories_same_community(
    release_webhook: Webhook,
    field_name: str,
) -> None:
    category = _create_category(release_webhook.community)
    form = _form_from_instance(release_webhook, {field_name: [category.pk]})
    assert form.is_valid() is True
    webhook = form.save()
    assert webhook == release_webhook
    assert category in getattr(webhook, field_name).all()


@pytest.mark.django_db
@pytest.mark.parametrize("field_name", ("require_categories", "exclude_categories"))
def test_webhook_form_modify_categories_different_community(
    release_webhook: Webhook,
    field_name: str,
) -> None:
    category = _create_category(Community.objects.create(name="Test"))
    form = _form_from_instance(release_webhook, {field_name: [category.pk]})
    assert form.is_valid() is False
    assert form.errors == {
        field_name: [
            "Select a valid choice. "
            f"{category.pk} "
            "is not one of the available choices."
        ]
    }


@pytest.mark.django_db
@pytest.mark.parametrize("field_name", ("require_categories", "exclude_categories"))
def test_webhook_form_create_categories_same_community(
    community: Community,
    field_name: str,
) -> None:
    category = _create_category(community)
    form = WebhookForm(
        data={
            "name": "test",
            "webhook_url": "https://example.com/",
            "webhook_type": WebhookType.mod_release,
            "is_active": True,
            "community": community,
            field_name: [category.pk],
        }
    )
    assert form.is_valid() is True
    webhook = form.save()
    assert category in getattr(webhook, field_name).all()


@pytest.mark.django_db
@pytest.mark.parametrize("field_name", ("require_categories", "exclude_categories"))
def test_webhook_form_create_categories_different_community(
    community: Community,
    field_name: str,
) -> None:
    category = _create_category(Community.objects.create(name="Test"))
    form = WebhookForm(
        data={
            "name": "test",
            "webhook_url": "https://example.com/",
            "webhook_type": WebhookType.mod_release,
            "is_active": True,
            "community": community,
            field_name: [category.pk],
        }
    )

    expected_error = "All categories must match the community of the Webhook"
    assert form.is_valid() is False
    assert form.errors == {"__all__": [expected_error]}


@pytest.mark.django_db
def test_webhook_form_admin_variant(release_webhook: Webhook):
    form1 = WebhookAdminForm(instance=release_webhook)
    assert form1.fields["exclude_categories"].queryset.query.is_empty() is False
    assert form1.fields["require_categories"].queryset.query.is_empty() is False
    form2 = WebhookAdminForm()
    assert form2.fields["exclude_categories"].queryset.query.is_empty() is True
    assert form2.fields["require_categories"].queryset.query.is_empty() is True
