from django.core.management.base import BaseCommand, CommandError
from neurovault.apps.statmaps.utils import is_search_compatible
from neurovault.apps.statmaps.models import Image

import os
import gc
import timeit
import numpy as np
import pickle
import nearpy

class Timer:
    def __init__(self, timer=None, disable_gc=False, verbose=True):
        if timer is None:
            timer = timeit.default_timer
        self.timer = timer
        self.disable_gc = disable_gc
        self.verbose = verbose
        self.start = self.end = self.interval = None
    def __enter__(self):
        if self.disable_gc:
            self.gc_state = gc.isenabled()
            gc.disable()
        self.start = self.timer()
        return self
    def __exit__(self, *args):
        self.end = self.timer()
        if self.disable_gc and self.gc_state:
            gc.enable()
        self.interval = self.end - self.start
        if self.verbose:
            print('time taken: %f seconds' % self.interval)


class Command(BaseCommand):
    args = '<times_to_run>'
    help = 'bench'

    def handle(self, *args, **options):
        ### Build Engine
        ## Main parameters
        n_bits = 7
        hash_counts = 40
        distance = nearpy.distances.EuclideanDistance()
        ## Filter
        filter_N = nearpy.filters.NearestFilter(100)


        # Get the size of the reduced representation atm
        for image in Image.objects.all():
            try:
                os.path.exists(str(image.reduced_representation.file))
                feature = np.load(image.reduced_representation.file)
                feature_dimension = feature.shape[0]
                break
            except ValueError:
                print "This image (%s) has no reduced representation" % image.pk

        # Create hash from scratch
        lshash = []
        ## Hash building
        # Random binary projections
        for k in xrange(hash_counts):
            nearpy_rbp = nearpy.hashes.RandomBinaryProjections('rbp_%d' % k, n_bits)
            lshash.append(nearpy_rbp)


        ## Create Engine
        engine = nearpy.Engine(feature_dimension, lshashes=lshash, distance=distance,
                                      vector_filters=[filter_N])  # storage=redis_storage

        ## Fill the Engine
        t = Timer()
        with t:
            for i, image in enumerate(Image.objects.all()):
                try:
                    os.path.exists(str(image.reduced_representation.file))
                    os.path.exists(str(image.thumbnail.file))
                    if is_search_compatible(image.pk):
                        feature = np.load(image.reduced_representation.file)
                        print "Length:", len(feature.tolist()), "Image:", image.pk
                        feature[np.isnan(feature)] = 0
                        engine.store_vector(feature.tolist(), image.pk)
                    else:
                        print "Image with PK %s has reduced representation but is not search compatible" % image.pk
                except ValueError:
                    print "This image (%s) has no reduced representation or thumbnail" % image.pk

            pickle.dump(engine,
                        open('/code/neurovault/apps/statmaps/tests/engine.p', "wb"))

        print "Engine built for %s images in %s seconds" % (i+1, t.interval)



























# # Get 100 features, for dimension selection and in case PCA is selected
# i = 0
# for image in Image.objects.all():
#     try:
#         os.path.exists(str(image.reduced_representation.file))
#         feature = np.load(image.reduced_representation.file)
#         if i == 0:
#             features = np.empty([99, feature.shape[0]])
#             features[i, :] = feature
#             i += 1
#         else:
#             features[i, :] = feature
#             i += 1
#         if i == 99:
#             break
#     except ValueError:
#         print "This image (%s) has no reduced representation" % image.pk
#

#########
# REDIS #
#########
# redis_object = redis.Redis(host='redis', port=6379, db=0)
# redis_storage = nearpy.storage.RedisStorage(redis_object)
# config = redis_storage.load_hash_configuration('neurovault')
# if config is None:

# Config is None: create hash from scratch, with 10 projections
# lshash = []
## Hash building
# Random binary projections
# for k in xrange(hash_counts):
#     nearpy_rbp = nearpy.hashes.RandomBinaryProjections('rbp_%d' % k, n_bits)
#     lshash.append(nearpy_rbp)
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
