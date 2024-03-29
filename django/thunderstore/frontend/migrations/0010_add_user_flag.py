# Generated by Django 3.1.7 on 2023-05-23 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0003_add_user_flag"),
        ("frontend", "0009_add_nav_links"),
    ]

    operations = [
        migrations.AddField(
            model_name="dynamichtml",
            name="exclude_user_flags",
            field=models.ManyToManyField(
                blank=True,
                help_text="Hidden from user with at least one of these flags",
                related_name="dynamic_html_exclusions",
                to="account.UserFlag",
            ),
        ),
        migrations.AddField(
            model_name="dynamichtml",
            name="require_user_flags",
            field=models.ManyToManyField(
                blank=True,
                help_text="Shown to users with at least one of these flags",
                related_name="dynamic_html_inclusions",
                to="account.UserFlag",
            ),
        ),
    ]
