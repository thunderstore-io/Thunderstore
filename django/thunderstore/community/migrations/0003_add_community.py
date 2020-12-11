# Generated by Django 3.0.4 on 2020-12-11 15:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0002_add_webhook_exclude_categories'),
    ]

    operations = [
        migrations.CreateModel(
            name='Community',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime_created', models.DateTimeField(auto_now_add=True)),
                ('datetime_updated', models.DateTimeField(auto_now=True)),
                ('identifier', models.CharField(max_length=256, unique=True, db_index=True)),
                ('name', models.CharField(max_length=256)),
            ],
            options={
                'verbose_name': 'community',
                'verbose_name_plural': 'communities',
            },
        ),
        migrations.AddField(
            model_name='packagecategory',
            name='community',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='package_categories', to='community.Community'),
        ),
        migrations.AddField(
            model_name='packagelisting',
            name='community',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='package_listings', to='community.Community'),
        ),
    ]
