from django.db import migrations


def preserve_existing_overrides(apps, schema_editor):
    # Packaged originals already live on PackageVersion. Only the surviving
    # override can be recovered for versions edited before history existed.
    with schema_editor.connection.cursor() as cursor:
        for document in ("readme", "changelog"):
            cursor.execute(
                f"""
                INSERT INTO repository_packageversionmarkdownrevision
                    (version_id, document, content, is_override,
                     recorded_at, edited_at, edited_by_id)
                SELECT id, %s, {document}_override, TRUE,
                       CURRENT_TIMESTAMP, {document}_override_edited_at,
                       {document}_override_edited_by_id
                FROM repository_packageversion
                WHERE {document}_override IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM repository_packageversionmarkdownrevision revision
                      WHERE revision.version_id = repository_packageversion.id
                        AND revision.document = %s
                  )
                """,
                [document, document],
            )


class Migration(migrations.Migration):
    dependencies = [
        ("repository", "0068_add_markdown_revision_history"),
    ]

    operations = [
        migrations.RunPython(preserve_existing_overrides, migrations.RunPython.noop),
    ]
