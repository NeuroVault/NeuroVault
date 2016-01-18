# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import taggit.managers
from django.db import migrations, models

def move_collection_data(apps, schema_editor):
    Image = apps.get_model("statmaps", "Image")
    BaseCollectionItem = apps.get_model("statmaps", "BaseCollectionItem")
    NIDMResults = apps.get_model("statmaps", "NIDMResults")
    ContentType = apps.get_model("contenttypes", "ContentType")
    for image in Image.objects.all():
        new_basebollectionitem = BaseCollectionItem()
        new_basebollectionitem.id = image.id
        new_basebollectionitem.name = image.name
        new_basebollectionitem.description = image.description
        new_basebollectionitem.add_date = image.add_date
        new_basebollectionitem.modify_date = image.modify_date
        new_basebollectionitem.collection = image.collection
        new_basebollectionitem.polymorphic_ctype = image.polymorphic_ctype
        new_basebollectionitem.tags = image.tags
        new_basebollectionitem.save()
        image.basecollectionitem_ptr = new_basebollectionitem
        image.save()

    for image in NIDMResults.objects.all():
        new_basebollectionitem = BaseCollectionItem()
        new_basebollectionitem.name = image.name
        new_basebollectionitem.description = image.description
        new_basebollectionitem.add_date = image.add_date
        new_basebollectionitem.modify_date = image.modify_date
        new_basebollectionitem.collection = image.collection
        new_basebollectionitem.polymorphic_ctype = ContentType.objects.get(app_label="statmaps", model="nidmresults")
        new_basebollectionitem.tags = image.tags
        image.basecollectionitem_ptr = new_basebollectionitem
        image.save()

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0061_add_base_class'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='basecollectionitem_ptr',
            field=models.IntegerField(default=0, serialize=False, null=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='nidmresults',
            name='basecollectionitem_ptr',
            field=models.IntegerField(default=0, serialize=False, null=True),
            preserve_default=False,
        ),
        migrations.RunPython(move_collection_data),
    ]
