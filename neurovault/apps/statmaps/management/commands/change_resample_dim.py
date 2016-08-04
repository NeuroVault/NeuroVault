from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile

from pybraincompare.mr.transformation import make_resampled_transformation_vector

import timeit
import os
from neurovault.apps.statmaps.models import Image
from six import BytesIO
import numpy as np
import nibabel as nib


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


def change_resample_dim(resample_dim):
    count = Image.objects.count()

    t = Timer()
    with t:
        for i, image in enumerate(Image.objects.all()):
            print "Fixing image %d (%d/%d)"%(image.pk, i+1, count)

            try:
                os.path.exists(str(image.reduced_representation.file)) # Is there any reduced_representation?
                os.remove(str(image.reduced_representation.file)) # if so, delete it

                nii_obj = nib.load(image.file.path)
                image_vector = make_resampled_transformation_vector(nii_obj, resample_dim)

                f = BytesIO()
                np.save(f, image_vector)
                f.seek(0)
                content_file = ContentFile(f.read())
                # and save a new one:
                image.reduced_representation.save("transform_%smm_%s.npy" % (resample_dim[0], image.pk), content_file)
                print "Resampled!"

            except ValueError or IOError:
                print "This image needs no resampling due to not previous resampled transformation"

    print "%s images resampled in %s seconds" % (i, t.interval)


class Command(BaseCommand):
    args = '<resamp dim>'
    help = 'change resample dim'

    def handle(self, *args, **options):

        if args:
            dim = int(args[0])
            resample_dim = [dim, dim, dim]
        else:
            resample_dim = [16,16,16]

        change_resample_dim(resample_dim)

