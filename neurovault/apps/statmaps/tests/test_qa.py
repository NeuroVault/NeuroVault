import os

import nibabel as nb
import numpy as np
from django.test import TestCase

from neurovault.apps.statmaps.models import BaseStatisticMap
from neurovault.apps.statmaps.utils import is_thresholded, infer_map_type


class QATest(TestCase):

    def setUp(self):
        this_path = os.path.abspath(os.path.dirname(__file__))
        self.brain = nb.load(os.path.join(this_path, "../static", "anatomical", "MNI152.nii.gz"))
        self.roi_map = nb.load(os.path.join(this_path, "test_data", "statmaps", "WA3.nii.gz"))
        self.parcellation = nb.load(os.path.join(this_path, "test_data", "TTatlas.nii.gz"))
        # We will fill in brain mask with this percentage of randomly placed values
        self.ratios = [0.0,0.1,0.15,0.2,0.25,0.3,0.4,0.5,0.6,0.96, 0.98]
        self.thresholded = [False,False,False,False,False,False,False,False,False,True,True]

    def testThresholded(self):
        for p,t in zip(self.ratios, self.thresholded):
            empty_data = np.ones(self.brain.shape)
            if p != 0.0:
                number_voxels = int(np.floor(p * empty_data.size))
                random_idx = np.random.choice(range(empty_data.size), number_voxels, replace=False)
                empty_data[np.unravel_index(random_idx, empty_data.shape)] = 0
            empty_nii = nb.Nifti1Image(empty_data,affine=self.brain.get_affine(),header=self.brain.get_header())
            is_thr, ratio_bad = is_thresholded(nii_obj=empty_nii)
            print "Zeroed %s of values, is_thresholded returns [%s:%s]" %(p,is_thr,ratio_bad)
            self.assertAlmostEqual(p, ratio_bad, delta=0.001)
            self.assertEquals(t, is_thr)

    def testInferMapType(self):
        self.assertEquals(infer_map_type(self.roi_map), BaseStatisticMap.R)
        self.assertEquals(infer_map_type(self.parcellation), BaseStatisticMap.Pa)
        self.assertEquals(infer_map_type(self.brain), BaseStatisticMap.OTHER)