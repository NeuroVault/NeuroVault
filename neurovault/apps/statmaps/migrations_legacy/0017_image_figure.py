# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0016_auto_20141224_1338'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='figure',
            field=models.CharField(help_text=b'Which figure in the corresponding paper was this map displayed in?', max_length=200, null=True, verbose_name=b'Corresponding figure', blank=True),
            preserve_default=True,
        ),
    ]
