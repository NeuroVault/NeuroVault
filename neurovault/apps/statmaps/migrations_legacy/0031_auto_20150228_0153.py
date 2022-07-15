# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0030_auto_20150227_2329'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cognitiveatlascontrast',
            options={'ordering': ['name']},
        ),
        migrations.AlterModelOptions(
            name='cognitiveatlastask',
            options={'ordering': ['name']},
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='cognitive_paradigm_cogatlas',
            field=models.ForeignKey(verbose_name=b'Cognitive Paradigm', to='statmaps.CognitiveAtlasTask', help_text=b"Task (or lack of it) performed by the subjects in the scanner described using <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> terms", null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='contrast_definition_cogatlas',
            field=models.CharField(help_text=b"Link to <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> definition of this contrast", max_length=200, null=True, verbose_name=b'Cognitive Atlas definition', blank=True),
            preserve_default=True,
        ),
    ]
