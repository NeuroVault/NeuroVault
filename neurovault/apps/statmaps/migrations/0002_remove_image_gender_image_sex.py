# Generated by Django 4.2.4 on 2025-01-24 20:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='image',
            old_name='gender',
            new_name='sex'
        ),
    ]
