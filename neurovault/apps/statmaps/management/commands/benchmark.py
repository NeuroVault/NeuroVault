from django.core.management.base import BaseCommand, CommandError
import os.path
from neurovault.apps import statmaps
import zipfile
import subprocess
import tempfile
from neurovault.apps.statmaps.tasks import run_voxelwise_pearson_similarity


#from neurovault.apps.statmaps.models import  Image
import gc
import timeit
import time

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
    rgs = '<times_to_run times_to_run ...>'
    help = 'bench'

    def handle(self, *args, **options):
        from neurovault.apps.statmaps.models import Image
        Images = Image.objects.all().filter()

        print args
        if args:
            for times_to_run in args:
                print times_to_run

                for image in Images:
                    t = Timer()
                    with t:
                        run_voxelwise_pearson_similarity(image.pk)
                    time_taken = t.interval
                    print time_taken

        else:
            for image in Images:
                t = Timer()
                with t:
                    run_voxelwise_pearson_similarity(image.pk)
                time_taken = t.interval




