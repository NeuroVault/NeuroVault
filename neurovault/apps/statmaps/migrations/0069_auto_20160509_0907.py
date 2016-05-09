# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations, models


def tag_sensitiveness(apps, schema_editor):
    # Find not lower case and duplicated tags and lowercase or delete them
    ValueTaggedItem = apps.get_model("statmaps", "ValueTaggedItem")
    Image = apps.get_model("statmaps", "Image")
    KeyValueTag = apps.get_model("statmaps", "KeyValueTag")

    value_tags = ValueTaggedItem.objects.all().distinct('object_id')

    for i_, value in enumerate(value_tags):
        image = Image.objects.all().filter(id=value.object_id)
        tags = image[0].tags.names()
        tags = [x.lower() for x in tags]
        tags = list(set(tags))[:]
        image[0].tags.clear()
        for j_, tag_name in enumerate(tags):
            image[0].tags.add(tag_name)

    # Find not lowercase KeyTags and delete them
    tags = KeyValueTag.objects.all()
    for i_, tag in enumerate(tags):
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

