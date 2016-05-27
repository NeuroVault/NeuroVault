from django.core.management.base import BaseCommand, CommandError
from neurovault.apps.statmaps.tasks import run_voxelwise_pearson_similarity


import gc
import timeit

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
        from neurovault.apps.statmaps.models import Image
        from neurovault.apps.statmaps.utils import get_images_to_compare_with, is_search_compatible

        Images = Image.objects.all()
        for image_candidate in Images:
            if is_search_compatible(image_candidate.pk):
                image = image_candidate
                break

        print args
        if args:
            for times_to_run in args:
                #TODO: program this with args, a loop will be enough
                print times_to_run

                for image in Images:
                    t = Timer()
                    with t:
                        run_voxelwise_pearson_similarity(image.pk)
                    time_taken = t.interval
                    print time_taken
        else:
            imgs_pks = get_images_to_compare_with(image.pk)
            if imgs_pks:
                imgs_pks.append(image.pk)
                num_imgs = len(imgs_pks)
                # Benchmark for 1/10 of the total images
                t = Timer()
                print "For 1/10 of the data (", num_imgs/10," images): "
                with t:
                    for pk in imgs_pks[0:num_imgs/10]:
                        run_voxelwise_pearson_similarity(pk)

                # Benchmark for 1/2 of the total images
                t = Timer()
                print "For 1/2 of the data (", num_imgs/2," images): "
                with t:
                    for pk in imgs_pks[0:num_imgs/2]:
                        run_voxelwise_pearson_similarity(pk)

                # Benchmark for all of the total images
                t = Timer()
                print "For all the data (", num_imgs," images): "
                with t:
                    for pk in imgs_pks[0:num_imgs]:
                        run_voxelwise_pearson_similarity(pk)
