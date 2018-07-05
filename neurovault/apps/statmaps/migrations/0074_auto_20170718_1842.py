# -*- coding: utf-8 -*-


from django.db import migrations, models
import neurovault.apps.statmaps.models
import neurovault.apps.statmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0073_auto_20161111_0033'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='private',
            field=models.BooleanField(default=False, verbose_name=b'Accessibility', choices=[(False, b'Public (The collection will be accessible by anyone and all the data in it will be distributed under CC0 license)'), (True, b'Private (The collection will be not listed in the NeuroVault index. It will be possible to shared it with others at a private URL.)')]),
        ),
        migrations.AlterField(
            model_name='image',
            name='surface_left_file',
            field=models.FileField(storage=neurovault.apps.statmaps.storage.DoubleExtensionStorage(), upload_to=neurovault.apps.statmaps.models.upload_img_to, null=True, verbose_name=b'File with the unthresholded LEFT hemisphere fsaverage surface map (.mgh, .curv, .gii)', blank=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='surface_right_file',
            field=models.FileField(storage=neurovault.apps.statmaps.storage.DoubleExtensionStorage(), upload_to=neurovault.apps.statmaps.models.upload_img_to, null=True, verbose_name=b'File with the unthresholded RIGHT hemisphere fsaverage surface map (.mgh, .curv, .gii)', blank=True),
        ),
    ]
