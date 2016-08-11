import os
import shutil
import tempfile

from django.test import TestCase
from numpy.testing import assert_equal

from neurovault.apps.statmaps.models import Image, User, Collection
from neurovault.apps.statmaps.tests.utils import clearDB
from neurovault.apps.statmaps.tests.utils import save_statmap_form, save_atlas_form
from neurovault.apps.statmaps.utils import count_existing_comparisons, is_search_compatible, get_existing_comparisons
from neurovault.apps.statmaps.management.commands.rebuild_engine import Command


class QueryTestCase(TestCase):
    pk1 = None
    pk2 = None
    pk3 = None
    pk4 = None
    pearson_metric = None
    
    def setUp(self):
        clearDB()
        print "\n#### TESTING THRESHOLDED IMAGES IN COMPARISON\n"
        self.tmpdir = tempfile.mkdtemp()
        self.app_path = os.path.abspath(os.path.dirname(__file__))
        self.u1 = User.objects.create(username='neuro_vault2')
        self.comparisonCollection1 = Collection(name='comparisonCollection1', owner=self.u1,
                                                DOI='10.3389/fninf.2015.00008')
        self.comparisonCollection1.save()
        self.comparisonCollection2 = Collection(name='comparisonCollection2', owner=self.u1,
                                                DOI='10.3389/fninf.2015.00009')
        self.comparisonCollection2.save()
        self.comparisonCollection3 = Collection(name='comparisonCollection3', owner=self.u1,
                                                DOI='10.3389/fninf.2015.00010')
        self.comparisonCollection3.save()
        self.comparisonCollection4 = Collection(name='comparisonCollection4', owner=self.u1,
                                                DOI='10.3389/fninf.2015.00011')
        self.comparisonCollection4.save()

        # Building Engine
        com = Command()
        com.handle()

        # Image 1 is an atlas
        print "Adding atlas image..."
        nii_path = os.path.join(self.app_path,"test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz")
        xml_path = os.path.join(self.app_path,"test_data/api/VentralFrontal_thr75_summaryimage_2mm.xml")
        image1 = save_atlas_form(nii_path=nii_path,xml_path=xml_path,collection = self.comparisonCollection1)
        self.pk1 = image1.id

        # Image 2 is a statistical map
        print "Adding statistical map..."
        image_path = os.path.join(self.app_path,'test_data/statmaps/beta_0001.nii.gz')
        image2 = save_statmap_form(image_path=image_path,collection = self.comparisonCollection2)
        self.pk2 = image2.id
        
        # Image 3 is a thresholded statistical map
        print "Adding thresholded statistical map..."
        image_paths = [os.path.join(self.app_path,'test_data/statmaps/box_0b_vs_1b.img'),
                       os.path.join(self.app_path,'test_data/statmaps/box_0b_vs_1b.hdr')]
        image3 = save_statmap_form(image_path=image_paths, collection = self.comparisonCollection3,ignore_file_warning=True)
        self.pk3 = image3.id


    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        clearDB()
        self.u1.delete()

    def counter(self, pk):
        if not is_search_compatible(pk):
            return 0
        else:
            return count_existing_comparisons(pk)

    def test_thresholded_image_comparison(self):
        # There should be no comparisons for a thresholded image
        print "testing comparisons for thresholded images"
        assert_equal(self.counter(self.pk3), 0)

        # There should be no comparisons for an atlas
        print "testing comparisons for atlases"
        assert_equal(self.counter(self.pk1), 0)


        # There should be no comparisons for statistical map because no other statistical maps
        print "testing comparisons for statistical maps"
        assert_equal(self.counter(self.pk2), 0)


        # Add another statistical map (the same, to ensure they fall in the same bucket)
        image_path = os.path.join(self.app_path,'test_data/statmaps/beta_0001.nii.gz')
        image4 = save_statmap_form(image_path=image_path, collection=self.comparisonCollection4)
        self.pk4 = image4.id

        # There should STILL be no comparisons for a thresholded image
        print "testing comparisons for thresholded images"
        assert_equal(self.counter(self.pk3), 0)


        # There should STILL be no comparisons for an of the atlas
        print "testing comparisons for atlases"
        assert_equal(self.counter(self.pk1), 0)


        # There should now be one comparison for each statistical map, two total
        print "testing comparisons for statistical maps"
        assert_equal(self.counter(self.pk2), 1)
        assert_equal(self.counter(self.pk4), 1)


        # This is the call that find_similar users to get images
        comparisons = get_existing_comparisons(self.pk4)
        pks = zip(*comparisons)[1]

        for pk in pks:
            im = Image.objects.get(pk=pk)
            assert_equal(im.is_thresholded,False)
