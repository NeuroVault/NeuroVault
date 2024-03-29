from django.core.management.base import BaseCommand, CommandError
from neurovault.apps.statmaps.tests.utils import clearDB, save_statmap_form
from neurovault.apps.statmaps.models import User, Collection
from neurovault.apps.statmaps.utils import get_similar_images
from neurovault.api.tests.utils import _setup_test_cognitive_atlas

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
            print(("time taken: %f seconds" % self.interval))


def down_data():
    import urllib.request, urllib.parse, urllib.error, json

    if not os.path.isdir("/code/neurovault/apps/statmaps/tests/bench"):
        os.makedirs("/code/neurovault/apps/statmaps/tests/bench")
        os.makedirs("/code/neurovault/apps/statmaps/tests/bench/images")
    if len(os.listdir("/code/neurovault/apps/statmaps/tests/bench/images")) == 0:
        (path, _) = urllib.request.urlretrieve(
            "https://ndownloader.figshare.com/files/5360999"
        )
        archive = tarfile.open(path)
        archive.extractall("/code/neurovault/apps/statmaps/tests/bench")
        archive.close()
        os.remove(path)


class Command(BaseCommand):
    args = "<times_to_run>"
    help = "bench"

    def handle(self, *args, **options):
        down_data()

        clearDB()
        User.objects.all().delete()
        app_path = "/code/neurovault/apps/statmaps/tests/bench"
        u1 = User.objects.create(username="neurovault3")

        num_files = len(os.listdir(os.path.join(app_path, "images/")))
        index_table = np.zeros(num_files)
        query_table = np.zeros(num_files)

        _setup_test_cognitive_atlas()

        for i, file in enumerate(os.listdir(os.path.join(app_path, "images/"))):
            # print 'Adding subject ' + file
            randomCollection = Collection(
                name="random" + file, owner=u1, DOI="10.3389/fninf.2015.00008" + str(i)
            )
            randomCollection.save()

            t = Timer()
            with t:
                image = save_statmap_form(
                    image_path=os.path.join(app_path, "images/", file),
                    collection=randomCollection,
                    image_name=file,
                    ignore_file_warning=True,
                )
            index_table[i] = t.interval
            np.savetxt(
                os.path.join(
                    app_path,
                    "results_index" + str(datetime.datetime.utcnow())[:10] + ".csv",
                ),
                index_table,
                delimiter=",",
            )

            t = Timer()
            with t:
                _dummy = get_similar_images(int(image.pk))
            query_table[i] = t.interval
            np.savetxt(
                os.path.join(
                    app_path,
                    "results_query" + str(datetime.datetime.utcnow())[:10] + ".csv",
                ),
                query_table,
                delimiter=",",
            )
