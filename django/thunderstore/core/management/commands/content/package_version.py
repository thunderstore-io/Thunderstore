from django.db.models import Q, signals

from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
    dummy_package_icon,
)
from thunderstore.repository.models import Package, PackageVersion
from thunderstore.storage.models import DataBlob, DataBlobGroup
from thunderstore.utils.iterators import print_progress

try:
    from ts_scanners.models.decompilation import Decompilation, DecompilationStatus
except ModuleNotFoundError as exc:
    if exc.name != "ts_scanners":
        raise
    Decompilation = None
    DecompilationStatus = None


class PackageVersionPopulator(ContentPopulator):
    def _clear_file_tree_seed_artifacts(self, group: DataBlobGroup) -> None:
        """Remove seeded entries and scanner rows so the group can be repopulated."""
        assert Decompilation is not None
        entry_qs = group.entries.all()
        blob_ids = list(entry_qs.values_list("blob_id", flat=True))
        if blob_ids:
            Decompilation.objects.filter(
                Q(target_id__in=blob_ids) | Q(result_id__in=blob_ids)
            ).delete()
        entry_qs.delete()
        if group.is_complete:
            group.is_complete = False
            group.save(update_fields=("is_complete",))

    def _build_mock_source(
        self, package_name: str, file_index: int, line_count: int
    ) -> str:
        lines = [
            "using System;",
            "",
            f"namespace {package_name}.Generated{file_index}",
            "{",
            f"    public static class GeneratedClass{file_index}",
            "    {",
        ]
        lines.extend(
            [
                f'        public static string Line{line_idx:03d}() => "Generated {line_idx} for {package_name}";'
                for line_idx in range(1, line_count + 1)
            ]
        )
        lines += [
            "    }",
            "}",
            "",
        ]
        return "\n".join(lines)

    def _seed_package_source_data(self) -> None:
        source_data_file_count = 5
        source_data_lines_per_file = 400

        if Decompilation is None or DecompilationStatus is None:
            print("Skipping package source seed data: ts_scanners is not available.")
            return

        version = (
            PackageVersion.objects.select_related("package")
            .order_by("-date_created")
            .filter(is_active=True)
            .first()
        )

        if not version:
            print("No active package version found for source data seeding.")
            return

        tree_name = f"File tree of package: {version.full_version_name}"

        file_tree = None
        if version.file_tree_id:
            existing = version.file_tree
            if existing.name == tree_name:
                file_tree = existing
            else:
                self._clear_file_tree_seed_artifacts(existing)
                version.file_tree = None
                version.save(update_fields=("file_tree",))
                existing.delete()

        if file_tree is None:
            file_tree = DataBlobGroup.objects.filter(name=tree_name).first()

        if file_tree is None:
            file_tree = DataBlobGroup.objects.create(name=tree_name)

        if version.file_tree_id != file_tree.id:
            version.file_tree = file_tree
            version.save(update_fields=("file_tree",))

        self._clear_file_tree_seed_artifacts(file_tree)

        for file_index in range(source_data_file_count):
            file_name = f"Generated/SourceFile{file_index + 1:02d}.dll"
            file_content = (
                f"binary content for {version.full_version_name} file {file_index + 1}"
            ).encode("utf-8")
            reference = file_tree.add_entry(file_content, file_name)

            source_text = self._build_mock_source(
                package_name=version.package.name,
                file_index=file_index + 1,
                line_count=source_data_lines_per_file,
            )
            result_blob = DataBlob.get_or_create(source_text.encode("utf-8"))

            Decompilation.objects.update_or_create(
                target=reference.blob,
                defaults={
                    "status": DecompilationStatus.SUCCESS,
                    "error_message": "",
                    "result": result_blob,
                },
            )

        file_tree.set_complete()
        print(f"Seeded package source data for {version.full_version_name}.")

    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating package versions...")

        # Disabling signals to avoid spamming cache clear calls and other
        # needless action
        # TODO: Implement a context manager for disabling cache refresh instead
        signals.post_save.disconnect(PackageVersion.post_save, sender=PackageVersion)
        signals.post_delete.disconnect(
            PackageVersion.post_delete, sender=PackageVersion
        )
        signals.post_save.disconnect(Package.post_save, sender=Package)
        signals.post_delete.disconnect(Package.post_delete, sender=Package)

        uploaded_icon = None

        for i, package in print_progress(
            enumerate(context.packages), len(context.packages)
        ):
            vercount = package.versions.count()
            for vernum in range(context.version_count - vercount):
                pv = PackageVersion(
                    package=package,
                    name=package.name,
                    version_number=f"{vernum + vercount}.0.0",
                    website_url="https://example.org",
                    description=f"Example mod {i}",
                    readme=f"# This is an example mod number {i}",
                    changelog=f"# Example changelog for mod number {i}",
                    file_size=5242880,
                )

                if context.reuse_icon and uploaded_icon:
                    pv.icon = uploaded_icon
                else:
                    pv.icon = dummy_package_icon()

                pv.save()
                uploaded_icon = pv.icon.name

            # Manually calling would-be signals once per package, as it doesn't
            # actually make use of the sender param at all (and can be None)
            package.handle_created_version(None)
            package.handle_updated_version(None)

        # Re-enabling previously disabled signals
        signals.post_save.connect(PackageVersion.post_save, sender=PackageVersion)
        signals.post_delete.connect(PackageVersion.post_delete, sender=PackageVersion)
        signals.post_save.connect(Package.post_save, sender=Package)
        signals.post_delete.connect(Package.post_delete, sender=Package)
        self._seed_package_source_data()

    def clear(self) -> None:
        print("Deleting existing package versions...")
        PackageVersion.objects.all().delete()
