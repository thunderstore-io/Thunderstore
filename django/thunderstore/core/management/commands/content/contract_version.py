from django_contracts.models import LegalContract, LegalContractVersion, PublishStatus
from thunderstore.core.management.commands.content.base import (
    LOREM_IPSUM,
    BaseContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.utils.iterators import print_progress


class LegalContractVersionPopulator(BaseContentPopulator):
    model_cls = LegalContractVersion
    name = "legal contract versions"
    obj_id_field = "markdown_content"
    obj_id_prefix = "## Test Contract "

    def create(self, contract: LegalContract, index: int) -> LegalContractVersion:
        return LegalContractVersion(
            **{
                "contract": contract,
                self.obj_id_field: "\n".join(
                    [
                        f"{self.obj_id_prefix}{index} - Markdown",
                        "",
                        LOREM_IPSUM,
                        "",
                        "### Subtitle",
                        "",
                        LOREM_IPSUM,
                    ]
                ),
                "html_content": "\n".join(
                    [
                        f"<h2>Test Contract {index} - HTML</h2>" "<br>",
                        f"<p>{LOREM_IPSUM}</p>",
                        "<br>",
                        "<h3>Subtitle</h3>" "<br>",
                        f"<p>{LOREM_IPSUM}</p>",
                    ]
                ),
            }
        )

    def populate(self, context: ContentPopulatorContext) -> None:
        print(f"Populating {self.name}...")

        last = self.get_last()
        objs = []
        for contract in context.contracts:
            existing = list(
                contract.versions.filter(
                    **{
                        f"{self.obj_id_field}__startswith": self.obj_id_prefix,
                        "contract": contract,
                    }
                )[: self.get_context_count(context)]
            )
            remainder = self.get_context_count(context) - len(existing)

            objs.extend(
                existing
                + [
                    self.create(contract, last + i)
                    for i in print_progress(range(remainder), remainder)
                ]
            )

        for obj in objs:
            if obj.publish_status != PublishStatus.PUBLISHED:
                obj.publish()

    def get_context_count(self, context: ContentPopulatorContext):
        return context.contract_version_count
