# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from neurovault.apps.statmaps.tasks import save_resampled_transformation_single
import os
import nearpy
#import redis


def change_resample_dim(apps, schema_editor):
    Image = apps.get_model("statmaps", "Image")
    count = Image.objects.count()
    for i, image in enumerate(Image.objects.all()):
        print "Fixing image %d (%d/%d)"%(image.pk, i+1, count)

        try:
            os.path.exists(str(image.reduced_representation.file))
            image.reduced_representation = save_resampled_transformation_single(image.pk,  resample_dim=[16, 16, 16])
            os.remove(str(image.reduced_representation.file))
        except ValueError:
            print "This image needs no resampling due to not previous resampled transformation"


def build_nearpy(apps, schema_editor):
    ### Build Engine
    ## Main parameters
    n_bits = 7
    hash_counts = 40
    distance = nearpy.distances.EuclideanDistance()

    #########
    # REDIS #
    #########
    # redis_object = redis.Redis(host='redis', port=6379, db=0)
    # redis_storage = nearpy.storage.RedisStorage(redis_object)
    # config = redis_storage.load_hash_configuration('neurovault')
    #if config is None:

    # Config is None: create hash from scratch, with 10 projections
    lshash = []
    ## Hash building
    # Random binary projections
    for k in xrange(hash_counts):
        nearpy_rbp = nearpy.hashes.RandomBinaryProjections('rbp_%d' % k, n_bits)
        lshash.append(nearpy_rbp)
        # PCA Binary projections
        # Get 100 dummy images to train the PCA space
        ## Apply:
        # for k in xrange(hash_counts):
        #     nearpy_rbp = nearpy.hashes.PCABinaryProjections('rbp_%d' % k, n_bits, features[:99, :].T)
        #     lshash.append(nearpy_rbp)

    # else:
    #     lshash = []
    #     for k in xrange(hash_counts):
    #         config = redis_storage.load_hash_configuration('rbp_%d' % k)
    #         # Config is existing, create hash with None parameters
    #         # Apply configuration loaded from redis
    #         lshash_aux = nearpy.hashes.RandomBinaryProjections(None, None)
    #         lshash_aux.apply_config(config)
    #         lshash.append(lshash_aux)
        # PCA Binary projections
        # Get 100 dummy images to train the PCA space
        ## Apply:
        # for k in xrange(hash_counts):
        #     nearpy_rbp = nearpy.hashes.PCABinaryProjections('rbp_%d' % k, n_bits, features[:99, :].T)
        #     lshash.append(nearpy_rbp)


    ## Filter
    filter_N = nearpy.filters.NearestFilter(100)



    ## Create Engine
    nearpy_engine = nearpy.Engine(features.shape[1], lshashes=lshash, distance=distance, vector_filters=[filter_N]) #storage=redis_storage


    ## Fill the Engine

    # get images
    Image = apps.get_model("statmaps", "Image")
    count = Image.objects.count()
    # populate engine
    for i, image in enumerate(Image.objects.all()):
        #

        print "Fixing image %d (%d/%d)"%(image.pk, i+1, count)

        try:
            for i, x in enumerate(features):
                nearpy_engine.store_vector(stats.zscore(x).tolist(), dict_feat[i])
        except ValueError:
            print "This image needs no resampling due to not previous resampled transformation"


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0070_auto_20160526_2216'),
    ]

    operations = [
        migrations.RunPython(change_resample_dim),
        migrations.RunPython(build_nearpy),
    ]
