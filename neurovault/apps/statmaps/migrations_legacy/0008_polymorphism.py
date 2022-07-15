# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
        ('statmaps', '0007_rename'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_statmaps.image_set', editable=False, to='contenttypes.ContentType', null=True),
            preserve_default=True,
        ),
    ]
