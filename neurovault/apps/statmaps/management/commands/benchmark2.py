from django.core.management.base import BaseCommand, CommandError
from neurovault.apps.statmaps.tasks import run_voxelwise_pearson_similarity
from neurovault.apps.statmaps.tests.utils import clearDB
from neurovault.apps.statmaps.models import Comparison, Similarity, User, Collection, Image
from neurovault.apps.statmaps.utils import get_images_to_compare_with, is_search_compatible
from neurovault.apps.statmaps.tests.utils import  save_statmap_form

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

        clearDB()
        app_path = os.path.abspath(os.path.dirname(__file__))
        u1 = User.objects.create(username='neurovault')
        comparisonCollection1 = Collection(name='comparisonCollection1', owner=self.u1,
                                                DOI='10.3389/fninf.2015.00008')
        comparisonCollection1.save()

        save_statmap_form(
            image_path=os.path.join(app_path, 'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz'),
            collection=self.comparisonCollection1,
            image_name="image1",
            ignore_file_warning=True)




        print args
        if args:
            print args
            #TODO: program this with args, a loop will be enough
        else:
            for root, dirs, filenames in os.walk(os.path.join(app_path,'test_data/bench/unthres/')):
                print root
                print dirs
                print filenames
                for file in filenames:
                    print 'Adding subject ' + file



                    file = indir + file
                    print file
                    # save_resampled_transformation_single(file)
                    # break






            # imgs_pks = get_images_to_compare_with(image.pk)
            # if imgs_pks:
            #     imgs_pks.append(image.pk)
            #     num_imgs = len(imgs_pks)
            #     # Benchmark for 1/10 of the total images
            #     t = Timer()
            #     print "For 1/10 of the data (", num_imgs/10," images): "
            #     with t:
            #         for pk in imgs_pks[0:num_imgs/10]:
            #             run_voxelwise_pearson_similarity.apply_sync(pk)