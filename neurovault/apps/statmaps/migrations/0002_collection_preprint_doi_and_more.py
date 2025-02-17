# Generated by Django 4.2.4 on 2025-02-03 21:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='preprint_DOI',
            field=models.CharField(blank=True, default=None, help_text='If there is not yet a publication, it is highly encouraged to provide a preprint DOI', max_length=200, null=True, verbose_name='Preprint DOI'),
        ),
        migrations.AddField(
            model_name='collection',
            name='publication_status',
            field=models.CharField(blank=True, choices=[('published', 'Yes'), ('submitted', 'Submitted'), ('in_preparation', 'In Preparation'), ('not_intended', 'No')], help_text='Is this collection associated with an existing, or planned publication?', null=True, verbose_name='Publication?'),
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='cognitive_paradigm_name',
            field=models.CharField(blank=True, help_text='Name of your task (if it)', null=True, verbose_name='Task Name'),
        ),
        migrations.AddField(
            model_name='statisticmap',
            name='cognitive_paradigm_short_description',
            field=models.CharField(blank=True, help_text='Describe your task', null=True, verbose_name='Task Description'),
        ),
        migrations.AlterField(
            model_name='collection',
            name='DOI',
            field=models.CharField(blank=True, default=None, help_text='Required for published collections.', max_length=200, null=True, unique=True, verbose_name='Publication DOI'),
        ),
        migrations.AlterField(
            model_name='collection',
            name='private',
            field=models.BooleanField(choices=[(False, 'Public'), (True, 'Private')], default=False, help_text='Public collections distributed under CC0 license. Private collections are not publicly indexed, but can be shared using a private URL.', verbose_name='Accessibility'),
        ),
        migrations.AlterField(
            model_name='image',
            name='figure',
            field=models.CharField(blank=True, help_text='Which figure in the corresponding paper was this map displayed in?', max_length=200, null=True, verbose_name='Manuscript figure'),
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='cognitive_paradigm_cogatlas',
            field=models.ForeignKey(help_text="Task performed by the subjects in the scanner described using <a href='http://www.cognitiveatlas.org/' target='_blank'>Cognitive Atlas</a>. If there's no match, select 'None / Other'. ", null=True, on_delete=django.db.models.deletion.PROTECT, to='statmaps.cognitiveatlastask', verbose_name='Cognitive Atlas Paradigm'),
        ),
        migrations.AlterField(
            model_name='statisticmap',
            name='cognitive_paradigm_description_url',
            field=models.URLField(blank=True, help_text='Link to a paper, poster, abstract describing in detail the task performed by the subject(s) in the scanner.', null=True, verbose_name='Description URL'),
        ),
    ]
