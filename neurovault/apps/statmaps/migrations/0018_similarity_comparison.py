# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def add_pearson_similarity(apps, schema_editor):
    Similarity = apps.get_model("statmaps", "Similarity")
    pearson_metric = Similarity(similarity_metric="pearson product-moment correlation coefficient",
                                     transformation="voxelwise",
                                     metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                     transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")
    pearson_metric.save()


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0017_image_figure'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comparison',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('similarity_score', models.FloatField(help_text=b'the comparison score between two or more statistical maps', verbose_name=b'the comparison score between two or more statistical maps')),
                ('image1', models.ForeignKey(related_name='image1', to='statmaps.Image')),
                ('image2', models.ForeignKey(related_name='image2', to='statmaps.Image')),
            ],
            options={
                'verbose_name': 'pairwise image comparison',
                'verbose_name_plural': 'pairwise image comparisons',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Similarity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('similarity_metric', models.CharField(help_text=b'the name of the similarity metric to describe a relationship between two or more images.', max_length=200, verbose_name=b'similarity metric name', db_index=True)),
                ('transformation', models.CharField(help_text=b'the name of the transformation of the data relevant to the metric', max_length=200, verbose_name=b'transformation of images name', db_index=True, blank=True)),
                ('metric_ontology_iri', models.URLField(help_text=b'If defined, a url of an ontology IRI to describe the similarity metric', verbose_name=b'similarity metric ontology IRI', db_index=True, blank=True)),
                ('transformation_ontology_iri', models.URLField(help_text=b'If defined, a url of an ontology IRI to describe the transformation metric', verbose_name=b'image transformation ontology IRI', db_index=True, blank=True)),
            ],
            options={
                'verbose_name': 'similarity metric',
                'verbose_name_plural': 'similarity metrics',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='comparison',
            name='similarity_metric',
            field=models.ForeignKey(to='statmaps.Similarity'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='comparison',
            unique_together=set([('image1', 'image2')]),
        ),
        migrations.RunPython(add_pearson_similarity),
    ]
