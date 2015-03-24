# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0021_auto_20150217_0532'),
    ]

    operations = [
        migrations.AlterField(
            model_name='statisticmap',
            name='modality',
            field=models.CharField(default=b'', help_text=b'Brain imaging procedure that was used to obtained to acquire the data.', max_length=200, verbose_name=b'Modality & Acquisition Type', choices=[(b'Unknown', b'Unknown'), (b'fMRI-BOLD', b'fMRI-BOLD'), (b'fMRI-CBF', b'fMRI-CBF'), (b'fMRI-CBV', b'fMRI-CBV'), (b'Diffusion MRI', b'Diffusion MRI'), (b'Structural MRI', b'Structural MRI'), (b'PET FDG', b'PET FDG'), (b'PET [15O]-water', b'PET [15O]-water'), (b'PET other', b'PET other'), (b'MEG', b'MEG'), (b'EEG', b'EEG'), (b'Other', b'Other')]),
            preserve_default=True,
        ),
    ]
