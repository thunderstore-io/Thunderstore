from typing import Any, Dict, List, Optional

from django.db.models import QuerySet

from django_contracts.models import LegalContract, PublishStatus
from thunderstore.core.management.commands.content.base import (
    BaseContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.utils.iterators import print_progress


class LegalContractPopulator(BaseContentPopulator):
    model_cls = LegalContract
    objs: Optional[List[LegalContract]] = None
    name = "legal contracts"
    obj_name_prefix = "Test Contract "
    obj_id_prefix = "test-contract-"
    obj_id_field = "slug"

    def get_existing(self) -> QuerySet:
        return self.model_cls.objects.filter(
            **{
                f"{self.obj_id_field}__startswith": self.obj_id_prefix,
            }
        )

    def create(self, index: int) -> LegalContract:
        return self.model_cls.objects.create(**self.get_create_kwargs(index))

    def get_create_kwargs(self, index: int) -> Dict[str, Any]:
        return {
            f"{self.obj_id_field}": f"{self.obj_id_prefix}{index}",
            "title": f"{self.obj_name_prefix}{index}",
        }

    def populate(self, context: ContentPopulatorContext) -> None:
        print(f"Populating {self.name}...")

        last = self.get_last()
        existing = list(self.get_existing()[: self.get_context_count(context)])
        remainder = self.get_context_count(context) - len(existing)

        self.objs = existing + [
            self.create(last + i) for i in print_progress(range(remainder), remainder)
        ]
        for obj in self.objs:
            if obj.publish_status != PublishStatus.PUBLISHED:
                obj.publish()

    def update_context(self, context: ContentPopulatorContext) -> None:
        if self.objs is not None:
            self.set_context_objs(context, self.objs)
        else:
            self.set_context_objs(
                context, self.get_existing()[: self.get_context_count(context)]
            )

    def get_context_count(self, context: ContentPopulatorContext):
        return context.contract_count

    def set_context_objs(
        self, context: ContentPopulatorContext, objs: List[Any]
    ) -> None:
        context.contracts = objs
