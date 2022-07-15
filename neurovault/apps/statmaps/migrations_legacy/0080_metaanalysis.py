# -*- coding: utf-8 -*-


from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('statmaps', '0079_auto_20181022_0048'),
    ]

    operations = [
        migrations.CreateModel(
            name='Metaanalysis',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=200)),
                ('description', models.TextField(null=True, blank=True)),
                ('status', models.CharField(default=b'active', max_length=200, null=True,
                                            blank=True, choices=[(b'active', b'active'), (b'inactive', b'inactive'), (b'completed', b'completed')])),
                ('maps', models.ManyToManyField(to='statmaps.StatisticMap', null=True,
                                                blank=True)),
                ('output_maps', models.ForeignKey(blank=True, to='statmaps.Collection',
                                                  null=True)),
                ('owner', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
