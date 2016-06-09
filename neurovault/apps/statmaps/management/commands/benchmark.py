from django.core.management.base import BaseCommand, CommandError
from neurovault.apps.statmaps.tests.utils import clearDB
from neurovault.apps.statmaps.models import Comparison, Similarity, User, Collection, Image
from neurovault.apps.statmaps.utils import get_existing_comparisons
from neurovault.apps.statmaps.tests.utils import  save_statmap_form

import os
import gc
import timeit, datetime, tarfile
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

def down_data():
    import urllib, json
    if not os.path.isdir('/code/neurovault/apps/statmaps/tests/bench'):
        os.makedirs('/code/neurovault/apps/statmaps/tests/bench')
        os.makedirs('/code/neurovault/apps/statmaps/tests/bench/images')
    if len(os.listdir('/code/neurovault/apps/statmaps/tests/bench/images')) == 0:
        (path, _) = urllib.urlretrieve("https://ndownloader.figshare.com/files/5360999")
        archive = tarfile.open(path)
        archive.extractall('/code/neurovault/apps/statmaps/tests/bench')
        archive.close()
        os.remove(path)


class Command(BaseCommand):
    args = '<times_to_run>'
    help = 'bench'

    def handle(self, *args, **options):
        down_data()

        clearDB()
        app_path = '/code/neurovault/apps/statmaps/tests/bench'
        u1 = User.objects.create(username='neurovault3')
        # comparisonCollection1 = Collection(name='comparisonCollection1', owner=u1,
        #                                         DOI='10.3389/fninf.2015.00008')
        # comparisonCollection1.save()
        #
        # save_statmap_form(
        #     image_path=os.path.join(app_path, 'images/0003.nii.gz'),
        #     collection=comparisonCollection1,
        #     image_name="image1",
        #     ignore_file_warning=True)

        num_files = len(os.listdir(os.path.join(app_path, 'images/')))
        index_table = np.zeros(num_files)
        query_table = np.zeros(num_files)

        for i, file in enumerate(os.listdir(os.path.join(app_path, 'images/'))):
            print 'Adding subject ' + file

            randomCollection = Collection(name='random' + file, owner=u1, DOI='10.3389/fninf.2015.00008' + str(i))
            randomCollection.save()

            t = Timer()
            with t:
                image = save_statmap_form(
                    image_path=os.path.join(app_path, 'images/', file),
                    collection=randomCollection,
                    image_name=file,
                    ignore_file_warning=True)
            index_table[i] = t.interval
            np.save(os.path.join(app_path, 'results_index'), index_table)

            t = Timer()
            with t:
                _dummy = get_existing_comparisons(image.pk).extra(
                    select={"abs_score": "abs(similarity_score)"}).order_by("-abs_score")[
                         0:100]  # "-" indicates descending # TODO: change this depending on the query function
            query_table[i] = t.interval
            np.save(os.path.join(app_path, 'results_query' + datetime.datetime.utcnow()), query_table)


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
