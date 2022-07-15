# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0051_auto_20150728_0340'),
    ]

    operations = [
        migrations.AddField(
            model_name='statisticmap',
            name='cognitive_contrast_cogatlas',
            field=models.ForeignKey(blank=True, to='statmaps.CognitiveAtlasContrast', help_text=b"Link to <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> definition of this contrast", null=True, verbose_name=b'Cognitive Atlas Contrast'),
            preserve_default=True,
        ),
    ]
