# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0026_populate_cogatlas'),
    ]

    operations = [
        migrations.AddField(
            model_name='statisticmap',
            name='cognitive_paradigm_cogatlas',
            field=models.CharField(help_text=b"Task (or lack of it) performed by the subjects in the scanner described using <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> terms", max_length=200, null=True, verbose_name=b'Cognitive Paradigm'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='modality',
            field=models.CharField(help_text=b'Brain imaging procedure that was used to acquire the data.', max_length=200, verbose_name=b'Modality & Acquisition Type', choices=[(b'fMRI-BOLD', b'fMRI-BOLD'), (b'fMRI-CBF', b'fMRI-CBF'), (b'fMRI-CBV', b'fMRI-CBV'), (b'Diffusion MRI', b'Diffusion MRI'), (b'Structural MRI', b'Structural MRI'), (b'PET FDG', b'PET FDG'), (b'PET [15O]-water', b'PET [15O]-water'), (b'PET other', b'PET other'), (b'MEG', b'MEG'), (b'EEG', b'EEG'), (b'Other', b'Other')]),
            preserve_default=True,
        ),
    ]
