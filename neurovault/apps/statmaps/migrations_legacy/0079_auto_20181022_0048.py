# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0078_auto_20180921_0126'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nidmresultstatisticmap',
            name='analysis_level',
            field=models.CharField(help_text=b'What level of summary data was used as the input to this analysis?', max_length=200, null=True, verbose_name=b'Analysis level', choices=[(b'S', b'single-subject'), (b'G', b'group'), (b'M', b'meta-analysis'), (b'Other', b'other')]),
        ),
        migrations.AlterField(
            model_name='nidmresultstatisticmap',
            name='number_of_subjects',
            field=models.IntegerField(help_text=b'Number of subjects used to generate this map', null=True, verbose_name=b'No. of subjects'),
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='analysis_level',
            field=models.CharField(help_text=b'What level of summary data was used as the input to this analysis?', max_length=200, null=True, verbose_name=b'Analysis level', choices=[(b'S', b'single-subject'), (b'G', b'group'), (b'M', b'meta-analysis'), (b'Other', b'other')]),
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='number_of_subjects',
            field=models.IntegerField(help_text=b'Number of subjects used to generate this map', null=True, verbose_name=b'No. of subjects'),
        ),
    ]
