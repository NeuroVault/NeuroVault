# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0039_add_thumbnail_image_field'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='comparison',
            index_together=set([('image2', 'similarity_metric'), ('image1', 'similarity_metric'), ('image1', 'image2', 'similarity_metric')]),
        ),
    ]
