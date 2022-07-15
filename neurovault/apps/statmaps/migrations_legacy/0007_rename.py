# -*- coding: utf-8 -*-


from django.db import models, migrations



class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0006_remove'),
    ]

    operations = [          
        migrations.RenameField(
            model_name='statisticmap',
            old_name='tmp_contrast_definition',
            new_name='contrast_definition',
        ),
        migrations.RenameField(
            model_name='statisticmap',
            old_name='tmp_contrast_definition_cogatlas',
            new_name='contrast_definition_cogatlas'
        ),
        migrations.RenameField(
            model_name='statisticmap',
            old_name='tmp_map_type',
            new_name='map_type'
        ),
        migrations.RenameField(
            model_name='statisticmap',
            old_name='tmp_smoothness_fwhm',
            new_name='smoothness_fwhm'
        ),
        migrations.RenameField(
            model_name='statisticmap',
            old_name='tmp_statistic_parameters',
            new_name='statistic_parameters'
        ),
    ]
