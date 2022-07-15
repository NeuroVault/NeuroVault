# -*- coding: utf-8 -*-


from django.contrib.auth import get_user_model
from django.db import migrations
from guardian.shortcuts import assign_perm


def populate_permissions(apps, schema_editor):
    Collection = apps.get_model("statmaps", "Collection")
    User = get_user_model()
    for collection in Collection.objects.all():
        user = User.objects.get(pk=collection.owner.pk)
        assign_perm('statmaps.delete_collection', user, collection)
         
        for contributor in [collection.owner, ] + list(collection.contributors.all()):
            user = User.objects.get(pk=contributor.pk)
            assign_perm('statmaps.change_collection', user, collection)
            for image in collection.basecollectionitem_set.all():
                assign_perm('statmaps.change_basecollectionitem', user, image)
                assign_perm('statmaps.delete_basecollectionitem', user, image)

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0064_fix_foreign_keys'),
    ]

    operations = [
        migrations.RunPython(populate_permissions),
    ]
