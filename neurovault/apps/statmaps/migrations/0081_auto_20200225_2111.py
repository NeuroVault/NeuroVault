# -*- coding: utf-8 -*-


from django.db import migrations, models
import neurovault.apps.statmaps.models
import neurovault.apps.statmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0080_metaanalysis'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='DOI',
            field=models.CharField(null=True, default=None, max_length=200, blank=True, help_text=b'Required if you want your maps to be archived in Stanford Digital Repository', unique=True, verbose_name=b'DOI of the corresponding paper'),
        ),
        migrations.AlterField(
            model_name='image',
            name='file',
            field=models.FileField(storage=neurovault.apps.statmaps.storage.DoubleExtensionStorage(), upload_to=neurovault.apps.statmaps.models.upload_img_to, max_length=500, verbose_name=b'File with the unthresholded volume map (.img, .nii, .nii.gz)'),
        ),
        migrations.AlterField(
            model_name='nidmresultstatisticmap',
            name='map_type',
            field=models.CharField(help_text=b'Type of statistic that is the basis of the inference', max_length=200, verbose_name=b'Map type', choices=[(b'T', b'T map'), (b'Z', b'Z map'), (b'F', b'F map'), (b'X2', b'Chi squared map'), (b'P', b'P map (given null hypothesis)'), (b'IP', b'1-P map ("inverted" probability)'), (b'M', b'multivariate-beta map'), (b'U', b'univariate-beta map'), (b'R', b'ROI/mask'), (b'Pa', b'parcellation'), (b'A', b'anatomical'), (b'V', b'variance'), (b'Other', b'other')]),
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='map_type',
            field=models.CharField(help_text=b'Type of statistic that is the basis of the inference', max_length=200, verbose_name=b'Map type', choices=[(b'T', b'T map'), (b'Z', b'Z map'), (b'F', b'F map'), (b'X2', b'Chi squared map'), (b'P', b'P map (given null hypothesis)'), (b'IP', b'1-P map ("inverted" probability)'), (b'M', b'multivariate-beta map'), (b'U', b'univariate-beta map'), (b'R', b'ROI/mask'), (b'Pa', b'parcellation'), (b'A', b'anatomical'), (b'V', b'variance'), (b'Other', b'other')]),
        ),
    ]
