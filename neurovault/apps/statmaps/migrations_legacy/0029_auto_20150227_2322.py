# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0028_auto_20150220_0307'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cognitiveatlascontrast',
            name='id',
        ),
        migrations.RemoveField(
            model_name='cognitiveatlastask',
            name='id',
        ),
        migrations.AlterField(
            model_name='cognitiveatlascontrast',
            name='cog_atlas_id',
            field=models.CharField(max_length=200, serialize=False, primary_key=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='cognitiveatlastask',
            name='cog_atlas_id',
            field=models.CharField(max_length=200, serialize=False, primary_key=True),
            preserve_default=True,
        ),
    ]
