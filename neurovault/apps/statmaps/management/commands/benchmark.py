from django.core.management.base import BaseCommand, CommandError
from neurovault.apps.statmaps.tests.utils import clearDB
from neurovault.apps.statmaps.models import Comparison, Similarity, User, Collection, Image
from neurovault.apps.statmaps.utils import get_existing_comparisons
from neurovault.apps.statmaps.tests.utils import  save_statmap_form

import os
import gc
import timeit
import numpy as np

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
    args = '<times_to_run times_to_run ...>'
    help = 'bench'

    def handle(self, *args, **options):

        clearDB()
        app_path = '/code/neurovault/apps/statmaps/tests'
        u1 = User.objects.create(username='neurovault3')
        comparisonCollection1 = Collection(name='comparisonCollection1', owner=u1,
                                                DOI='10.3389/fninf.2015.00008')
        comparisonCollection1.save()

        save_statmap_form(
            image_path=os.path.join(app_path, 'bench/unthres/0003.nii.gz'),
            collection=comparisonCollection1,
            image_name="image1",
            ignore_file_warning=True)

        i = 0
        num_files = len(os.listdir(os.path.join(app_path, 'bench/unthres/')))
        index_table = np.zeros(num_files)
        query_table = np.zeros(num_files)

        if args:
            if args[0] == "full":
                for file in os.listdir(os.path.join(app_path, 'bench/unthres/')):

                    print 'Adding subject ' + file

                    randomCollection = Collection(name='random' + file, owner=u1,
                                                  DOI='10.3389/fninf.2015.00008' + str(i))
                    randomCollection.save()

                    if i > 0 and i % 500 == 0:
                        t = Timer()
                        with t:
                            image = save_statmap_form(
                                image_path=os.path.join(app_path, 'bench/unthres/', file),
                                collection=randomCollection,
                                image_name=file,
                                ignore_file_warning=True)
                        index_table[i] = t.interval
                        np.save(os.path.join(app_path, 'bench/results_index_busy'), index_table)

                        t = Timer()
                        with t:
                            _dummy = get_existing_comparisons(image.pk).extra(
                                select={"abs_score": "abs(similarity_score)"}).order_by("-abs_score")[
                                     0:100]  # "-" indicates descending # TODO: change this depending on the query function
                        query_table[i] = t.interval
                        np.save(os.path.join(app_path, 'bench/results_query_busy'), query_table)
                    else:
                        image = save_statmap_form(
                            image_path=os.path.join(app_path, 'bench/unthres/', file),
                            collection=randomCollection,
                            image_name=file,
                            ignore_file_warning=True)
                    i += 1

        else:
            for file in os.listdir(os.path.join(app_path, 'bench/unthres/')):

                print 'Adding subject ' + file

                randomCollection = Collection(name='random'+file, owner=u1, DOI='10.3389/fninf.2015.00008'+str(i))
                randomCollection.save()

                t = Timer()
                with t:
                    image = save_statmap_form(
                        image_path=os.path.join(app_path, 'bench/unthres/', file),
                        collection=randomCollection,
                        image_name=file,
                        ignore_file_warning=True)
                #print "Time taken to index", i, " images: ", t.interval
                index_table[i] = t.interval
                np.save(os.path.join(app_path, 'bench/results_index_not_busy'), index_table)

                t = Timer()
                with t:
                    _dummy = get_existing_comparisons(image.pk).extra(select={"abs_score": "abs(similarity_score)"}).order_by("-abs_score")[0:100]  # "-" indicates descending # TODO: change this depending on the indexing function
                query_table[i] = t.interval
                np.save(os.path.join(app_path, 'bench/results_query_not_busy'), query_table)

                i += 1

# import matplotlib.pyplot as plt
# import numpy as np
# a = np.load('results_query_busy.npy')
# b = np.load('results_query_not_busy.npy')
# plt.plot(a,"ro",b,"bs")
# plt.xlabel('Number of Images')
# plt.ylabel('Seconds')
# plt.title('Query benchmark for actual implementation')
# plt.legend(['Busy server', 'Not busy'],loc=2)
# plt.show()