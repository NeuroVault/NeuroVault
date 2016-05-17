# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations, models


def tag_sensitiveness(apps, schema_editor):
    # Find not lower case and duplicated tags and lowercase or delete them
    ValueTaggedItem = apps.get_model("statmaps", "ValueTaggedItem")
    KeyValueTag = apps.get_model("statmaps", "KeyValueTag")
    # Get a dict of all key_tags and thier names
    tag_dict = {tag.name: tag.id for tag in KeyValueTag.objects.all()}

    # Find for all tagged_items if there is a lowercased case, replace or create
    for item in ValueTaggedItem.objects.all():
        if tag_dict.has_key(item.tag.name.lower()):
            item.tag_id = tag_dict.get(item.tag.name.lower())
            print item.tag_id
            item.save()
        else:  # if there was not a lowercase tag associated to it
            item.tag.name = item.tag.name.lower()
            item.tag.save()
            tag_dict[item.tag.name] = item.tag_id

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

