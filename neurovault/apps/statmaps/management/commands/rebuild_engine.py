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

        feature_dimension = None
        # Get the size of the reduced representation atm
        for image in Image.objects.all():
            try:
                os.path.exists(str(image.reduced_representation.file))
                feature = np.load(image.reduced_representation.file)
                feature_dimension = feature.shape[0]
                break
            except ValueError:
                print "This image (%s) has no reduced representation" % image.pk

        # This is an exceptional case, for situations that there is not images in the DB (tests)
        if not feature_dimension:
            feature_dimension = 450
            i = 0

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
