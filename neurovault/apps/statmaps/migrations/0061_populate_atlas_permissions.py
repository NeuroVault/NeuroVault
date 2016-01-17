# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from guardian.shortcuts import assign_perm
from django.db import migrations
from django.contrib.auth import get_user_model


def populate_atlas_permissions(apps, schema_editor):
    Collection = apps.get_model("statmaps", "Collection")
    Atlas = apps.get_model("statmaps", "Atlas")
    User = get_user_model()

    for collection in Collection.objects.all():
        for contributor in [collection.owner, ] + list(collection.contributors.all()):
            user = User.objects.get(pk=contributor.pk)
            for image in collection.image_set.instance_of(Atlas):
                assign_perm('statmaps.change_atlas', user, image)
                assign_perm('statmaps.delete_atlas', user, image)

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0060_auto_20160103_0406'),
    ]

    operations = [
        migrations.RunPython(populate_atlas_permissions),
    ]
