# -*- coding: utf-8 -*-


from django.db import models, migrations

class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0023_auto_20150218_1943'),
    ]

    operations = [
        migrations.CreateModel(
            name='CognitiveAtlasTask',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('cog_atlas_id', models.CharField(max_length=200)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='modality',
            field=models.CharField(help_text=b'Brain imaging procedure that was used to acquire the data.', max_length=200, verbose_name=b'Modality & Acquisition Type', choices=[(b'fMRI-BOLD', b'fMRI-BOLD'), (b'fMRI-CBF', b'fMRI-CBF'), (b'fMRI-CBV', b'fMRI-CBV'), (b'Diffusion MRI', b'Diffusion MRI'), (b'Structural MRI', b'Structural MRI'), (b'PET FDG', b'PET FDG'), (b'PET [15O]-water', b'PET [15O]-water'), (b'PET other', b'PET other'), (b'MEG', b'MEG'), (b'EEG', b'EEG')]),
            preserve_default=True,
        )
    ]
