# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0037_auto_20150307_0222'),
    ]

    operations = [
        migrations.RenameField('collection', 'skip_factor', 'skip_distance'),
        migrations.AlterField(
            model_name='collection',
            name='length_of_trials',
            field=models.TextField(help_text=b"Length of individual trials in seconds. If variable, enter 'variable'. ", null=True, verbose_name=b'Length of trials', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='collection',
            name='object_image_type',
            field=models.CharField(help_text=b"What type of image was used to determine the transformation to the atlas? (e.g. 'T1', 'T2', 'EPI')", max_length=200, null=True, verbose_name=b'Object image type', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='collection',
            name='proportion_male_subjects',
            field=models.FloatField(blank=True, help_text=b'The proportion (not percentage) of subjects who were male', null=True, verbose_name=b'Prop. male subjects', validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='cognitive_paradigm_cogatlas',
            field=models.ForeignKey(verbose_name=b'Cognitive Paradigm', to='statmaps.CognitiveAtlasTask', help_text=b"Task (or lack of it) performed by the subjects in the scanner described using <a href='http://www.cognitiveatlas.org/' target='_blank'>Cognitive Atlas</a> terms", null=True),
            preserve_default=True,
        ),
    ]
