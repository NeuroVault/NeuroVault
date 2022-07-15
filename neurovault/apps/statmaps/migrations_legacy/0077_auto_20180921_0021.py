# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0076_auto_20180702_0152'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='BMI',
            field=models.FloatField(null=True, verbose_name=b'Body Mass Index (kg/m2)', blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='age',
            field=models.FloatField(null=True, verbose_name=b'Age (years)', blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='bis11_score',
            field=models.FloatField(null=True, verbose_name=b'Barratt Impulsiveness Scale (BIS-11) score', blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='bis_bas_score',
            field=models.FloatField(null=True, verbose_name=b'Behavioral inhibition, behavioral activation (BIS/BAS) score', blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='days_since_menstruation',
            field=models.FloatField(null=True, verbose_name=b'Number of days since menstruation', blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='ethnicity',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name=b'Ethnicity (US Census definition)', choices=[(b'H', b'Hispanic or Latino'), (b'NH', b'Not Hispanic or Latino')]),
        ),
        migrations.AddField(
            model_name='image',
            name='fat_percentage',
            field=models.FloatField(null=True, verbose_name=b'% body fat', blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='gender',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name=b'Gender', choices=[(b'M', b'Male'), (b'F', b'Female'), (b'O', b'Other')]),
        ),
        migrations.AddField(
            model_name='image',
            name='handedness',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name=b'Handedness', choices=[(b'L', b'Left'), (b'R', b'Right')]),
        ),
        migrations.AddField(
            model_name='image',
            name='hours_since_last_meal',
            field=models.FloatField(null=True, verbose_name=b'Time since last meal (hours)', blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='mean_PDS_score',
            field=models.FloatField(null=True, verbose_name=b'Mean Puberty Development Scale score', blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='race',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name=b'Race (US Census definition)', choices=[(b'W', b'White'), (b'B', b'Black or African American'), (b'I', b'American Indian or Alaska Native'), (b'A', b'Asian'), (b'H', b'Native Hawaiian or Other Pacific Islander')]),
        ),
        migrations.AddField(
            model_name='image',
            name='spsrq_score',
            field=models.FloatField(null=True, verbose_name=b'Sensitivity to Punishment and Sensitivity to Reward Questionnaire (SPSRQ) score', blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='tanner_stage',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name=b'Tanner stage', choices=[(b'I', b'I'), (b'II', b'II'), (b'III', b'III'), (b'IV', b'IV'), (b'V', b'V')]),
        ),
        migrations.AddField(
            model_name='image',
            name='waist_hip_ratio',
            field=models.FloatField(null=True, verbose_name=b'waist-hip-ratio', blank=True),
        ),
    ]
