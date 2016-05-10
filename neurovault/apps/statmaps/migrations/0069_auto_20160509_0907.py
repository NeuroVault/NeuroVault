# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations, models


def tag_sensitiveness(apps, schema_editor):
    # Find not lower case and duplicated tags and lowercase or delete them
    ValueTaggedItem = apps.get_model("statmaps", "ValueTaggedItem")
    Image = apps.get_model("statmaps", "Image")
    KeyValueTag = apps.get_model("statmaps", "KeyValueTag")

    for value in ValueTaggedItem.objects.all().distinct('object_id'):
        image = Image.objects.all().filter(id=value.object_id)
        tags = image[0].tags.names()
        tags = [x.lower() for x in tags]
        tags = list(set(tags))[:]
        image[0].tags.clear()
        for tag_name in tags:
            image[0].tags.add(tag_name)

    # Find not lowercase KeyTags and delete them
    for tag in KeyValueTag.objects.all():
        if not tag.name.islower():
            print "Deleting %s" % tag.name
            tag.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0068_auto_20160429_0743'),
    ]

    operations = [
        migrations.RunPython(tag_sensitiveness),
    ]

