"""Comparisons and meta-analyses now reference Item rows (same ids as before)."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("statmaps", "0007_copy_items"),
    ]

    operations = [
        migrations.AlterField(
            model_name='comparison',
            name='image1',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='image1', to='statmaps.item'),
        ),
        migrations.AlterField(
            model_name='comparison',
            name='image2',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='image2', to='statmaps.item'),
        ),
        migrations.AlterField(
            model_name='metaanalysis',
            name='maps',
            field=models.ManyToManyField(blank=True, to='statmaps.item'),
        ),
    ]
