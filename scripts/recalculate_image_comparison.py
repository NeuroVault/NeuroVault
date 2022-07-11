'''
Created on 10 April 2015

@author: vsochat

Update database with image transformations
'''
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

from neurovault.apps.statmaps.models import Similarity, Comparison, Image, Collection
from neurovault.apps.statmaps.tasks import run_voxelwise_pearson_similarity, save_resampled_transformation_single

# Images should have the "transform" field after applying migrations (I think)

# First create/update the image similarity metric
pearson_metric = Similarity.objects.update_or_create(similarity_metric="pearson product-moment correlation coefficient",
                                     transformation="voxelwise",
                                     metric_ontology_iri="http://webprotege.stanford.edu/RCS8W76v1MfdvskPLiOdPaA",
                                     transformation_ontology_iri="http://webprotege.stanford.edu/R87C6eFjEftkceScn1GblDL")

# Delete all old comparisons
all_comparisons = Comparison.objects.all().delete()

# Delete all reduced representations
total_images = Image.objects.count()
counter = 0
for img in Image.objects.all():
    if not img.reduced_representation or not os.path.exists(img.reduced_representation.path):
        if hasattr(img, "is_thresholded") and not img.is_thresholded:
            print("Working on image %d"%img.pk)
            save_resampled_transformation_single(img.pk)
    counter += 1
    print("Recreated %d npys out of %d (pk = %d)"%(counter, total_images, img.pk))

# Filter down to images that are not private, not thresholded
# Now, we need to generate a "comparison" object for all files in the database
# We will use a celery task (as this will be integrated into upload workflow)
for collection in Collection.objects.filter(DOI__isnull=False):
    for image in collection.basecollectionitem_set.instance_of(Image).all():
        print("Calculating pearson similarity for images %s" %image)
        run_voxelwise_pearson_similarity(image.pk)
