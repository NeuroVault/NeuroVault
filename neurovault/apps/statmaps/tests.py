from django.test import TestCase
import tempfile
import os
import shutil
from neurovault.apps.statmaps.utils import detect_afni4D, split_afni4D_to_3D


class Afni4DTest(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        app_path = os.path.abspath(os.path.dirname(__file__))
        self.afni_file = os.path.join(app_path,'static/test_data/TTatlas.nii.gz')
        self.nii_file = os.path.join(app_path,'static/anatomical/MNI152.nii.gz')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    """
    TTatlas is the example 4D file that ships with afni, has two sub-bricks:

    vagrant@localhost$ 3dinfo  TTatlas.nii.gz
    ++ 3dinfo: AFNI version=AFNI_2011_12_21_1014 (Nov 22 2014) [64-bit]
    <<... snip ..>>
    Number of values stored at each pixel = 2
      -- At sub-brick #0 'uu3[0]' datum type is byte:            0 to 77
         keywords = uu3+tlrc[0] ; TTatlas+tlrc[0] ; uu3+tlrc[0]
      -- At sub-brick #1 'uu5[0]' datum type is byte:            0 to 151
         keywords = uu5+tlrc[0] ; TTatlas+tlrc[1] ; uu5+tlrc[0]
    """

    def testAfni4DSlicing(self):
        test_afni = detect_afni4D(self.afni_file)
        test_non_afni = detect_afni4D(self.nii_file)

        bricks = split_afni4D_to_3D(self.afni_file,tmp_dir=self.tmpdir)

        # check detection of 4D is correct
        self.assertTrue(test_afni)
        self.assertFalse(test_non_afni)

        # check for 2 sub bricks
        self.assertEquals(len(bricks),2)

        # check that brick labels match afni 3dinfo binary output
        self.assertEquals(bricks[0][0],'uu3[0]')
        self.assertEquals(bricks[1][0],'uu5[0]')

        # check that sliced niftis exist at output location
        self.assertTrue(os.path.exists(bricks[0][1]))
        self.assertTrue(os.path.exists(bricks[1][1]))
