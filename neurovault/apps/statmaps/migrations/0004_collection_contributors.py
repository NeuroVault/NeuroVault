# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('statmaps', '0003_collection_journal_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='contributors',
            field=models.ManyToManyField(related_name=b'collection_contributors', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
