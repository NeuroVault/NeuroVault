# -*- coding: utf-8 -*-


import taggit.managers
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0062_move_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='image',
            name='add_date',
        ),
        migrations.RemoveField(
            model_name='image',
            name='collection',
        ),
        migrations.RemoveField(
            model_name='image',
            name='description',
        ),
        migrations.RemoveField(
            model_name='image',
            name='id',
        ),
        migrations.RemoveField(
            model_name='image',
            name='modify_date',
        ),
        migrations.RemoveField(
            model_name='image',
            name='name',
        ),
        migrations.RemoveField(
            model_name='image',
            name='polymorphic_ctype',
        ),
        migrations.RemoveField(
            model_name='image',
            name='tags',
        ),
        migrations.AlterUniqueTogether(
            name='nidmresults',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='nidmresults',
            name='add_date',
        ),
        migrations.RemoveField(
            model_name='nidmresults',
            name='collection',
        ),
        migrations.RemoveField(
            model_name='nidmresults',
            name='description',
        ),
        migrations.RemoveField(
            model_name='nidmresults',
            name='id',
        ),
        migrations.RemoveField(
            model_name='nidmresults',
            name='modify_date',
        ),
        migrations.RemoveField(
            model_name='nidmresults',
            name='name',
        ),
        migrations.RemoveField(
            model_name='nidmresults',
            name='tags',
        ),
        migrations.AlterField(
            model_name='image',
            name='basecollectionitem_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, null=False, serialize=False, to='statmaps.BaseCollectionItem'),
        ),
        migrations.AlterField(
            model_name='nidmresults',
            name='basecollectionitem_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, null=False, serialize=False, to='statmaps.BaseCollectionItem'),
        ),
    ]
