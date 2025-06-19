from django.db import migrations

"""
This migration used to have logic for creating/updating default VisibilityFlags
for Package/PackageVersion/PackageListing models, but as the system is currently
not in active use and we have no logic ensuring the state is maintained
correctly, the data migration was removed as it was considered unnecessary but
would have made deployment take longer.

Instead, this stub was left around as to not brick migration history for
environments that might have already run the migration.
"""


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0036_packagelisting_visibility"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
