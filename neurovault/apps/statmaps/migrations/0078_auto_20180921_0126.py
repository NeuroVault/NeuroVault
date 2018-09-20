# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0077_auto_20180921_0021'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='nutbrain_food_choice_type',
            field=models.CharField(help_text=b'Choice conditions/image types', max_length=200, null=True, verbose_name=b'Food choice type', blank=True),
        ),
        migrations.AddField(
            model_name='collection',
            name='nutbrain_food_viewing_conditions',
            field=models.CharField(help_text=b'Image categories', max_length=200, null=True, verbose_name=b'Food viewing conditions', blank=True),
        ),
        migrations.AddField(
            model_name='collection',
            name='nutbrain_hunger_state',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name=b'Hunger state', choices=[(b'I', b'Fed (<1h after meal)'), (b'II', b'2-3 h fasted'), (b'III', b'4-6 h fasted'), (b'IV', b'7-9h fasted'), (b'V', b'fasted overnight (> 10h)'), (b'VI', b'36h fast')]),
        ),
        migrations.AddField(
            model_name='collection',
            name='nutbrain_odor_conditions',
            field=models.CharField(max_length=200, null=True, verbose_name=b'Odor conditions', blank=True),
        ),
        migrations.AddField(
            model_name='collection',
            name='nutbrain_taste_conditions',
            field=models.CharField(max_length=200, null=True, verbose_name=b'Taste conditions', blank=True),
        ),
    ]
