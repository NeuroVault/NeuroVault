# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations, models


def tag_sensitiveness(apps, schema_editor):
    # Find not lower case and duplicated tags and lowercase or delete them
    ValueTaggedItem = apps.get_model("statmaps", "ValueTaggedItem")
    KeyValueTag = apps.get_model("statmaps", "KeyValueTag")
    print ValueTaggedItem.objects.all().count()
    # Get a dict of all key_tags and thier names
    tag_dict = {tag.name: tag.id for tag in KeyValueTag.objects.all()}
    print tag_dict
    slug_dict = {tag.id: tag.slug for tag in KeyValueTag.objects.all()}

    # Find for all tagged_items if there is a lowercased case, replace or create
    for tag in KeyValueTag.objects.all():
        print "Tag was %s,with slug %s, with id %s" % (tag.name,tag.slug, tag.id)
        tag.name = tag.name.lower()
        tag.slug = slug_dict.get(tag_dict.get(tag.name))
        if tag_dict.has_key(tag.name):
            tag.id = tag_dict.get(tag.name)
        else:  # if there was not a lowercase tag associated to it
            tag_dict[tag.name] = tag.id
        tag.save()
        print "Tag now is %s,with slug %s, with id %s" % (tag.name, tag.slug, tag.id)

    # for item in ValueTaggedItem.objects.all():
    #     print dir(item.tag)
    #     print "Tag is %s,with slug %s, with id %s" % (item.tag.name,item.tag.slug, item.tag.id)


    # Find not lowercase KeyTags and delete them
    for tag in KeyValueTag.objects.all():
        if not tag.name.islower():
            print "Deleting %s" % tag.name
            tag.delete()

    print ValueTaggedItem.objects.all().count()
    print a

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0068_auto_20160429_0743'),
    ]

    operations = [
        migrations.RunPython(tag_sensitiveness),
    ]

