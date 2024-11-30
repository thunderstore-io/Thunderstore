# Generated by Django 3.1.7 on 2024-05-23 17:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("frontend", "0012_add_footer_links"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dynamichtml",
            name="placement",
            field=models.CharField(
                choices=[
                    ("ads_txt", "ads_txt"),
                    ("robots_txt", "robots_txt"),
                    ("html_head", "html_head"),
                    ("html_body_beginning", "html_body_beginning"),
                    ("content_beginning", "content_beginning"),
                    ("footer_top", "footer_top"),
                    ("footer_bottom", "footer_bottom"),
                    ("content_end", "content_end"),
                    ("package_page_actions", "package_page_actions"),
                    ("main_content_left", "main_content_left"),
                    ("main_content_right", "main_content_right"),
                    ("cyberstorm_header", "cyberstorm_header"),
                    ("cyberstorm_body_beginning", "cyberstorm_body_beginning"),
                    ("cyberstorm_content_left", "cyberstorm_content_left"),
                    ("cyberstorm_content_right", "cyberstorm_content_right"),
                ],
                db_index=True,
                max_length=256,
            ),
        ),
    ]
