
from typing import Type
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from ts_kafka.producer import publish_event
from thunderstore.core.kafka import AccountEvents, KafkaTopics

User = settings.AUTH_USER_MODEL

@receiver(post_save, sender=User)
def on_user_saved(sender: Type[User], instance: User, created: bool, **kwargs):
    # Ignore modifications
    if not created:
        return

    transaction.on_commit(
        lambda: publish_event(
            KafkaTopics.METRICS_ACCOUNTS,
            key=AccountEvents.USER_CREATED,
            value={
                "user_id": str(instance.id),
                "username": instance.username,
                "auth_provider": None, # Where do we get this?
            },
        )
    )
