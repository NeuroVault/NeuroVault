# -*- coding: utf-8 -*-


from django.db import migrations, models

def add_nutrition_and_developmental(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    Community = apps.get_model("statmaps", "Community")

    Community.objects.create(label="developmental", short_desc="Developmental Neuroscience")
    Community.objects.create(label="nutritional", short_desc="Nutritional Neuroscience")


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0075_auto_20180416_0413'),
    ]

    operations = [
        migrations.CreateModel(
            name='Community',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(unique=True, max_length=200, verbose_name=b'Lexical label of the community')),
                ('short_desc', models.CharField(max_length=200, verbose_name=b'Short description of the community')),
            ],
        ),
        migrations.AddField(
            model_name='collection',
            name='communities',
            field=models.ManyToManyField(related_query_name=b'collection', related_name='collections', default=None, to='statmaps.Community', blank=True, help_text=b'Is this collection part of any special Community?', verbose_name=b'Communities'),
        ),
        migrations.RunPython(add_nutrition_and_developmental),

    ]
