from django.test import TestCase
from django.test import Client
from django.core.urlresolvers import reverse
from neurovault.apps.statmaps.models import Collection,User
from uuid import uuid4
import tempfile
import os
import shutil
from neurovault.apps.statmaps.utils import detect_afni4D, split_afni4D_to_3D
from glob import glob


class CollectionSharingTest(TestCase):

    def setUp(self):
        self.user = {}
        self.client = {}
        for role in ['owner','contrib','someguy']:
            self.user[role] = User.objects.create_user('%s_%s' % (role,
                                                       self.uniqid()), None,'pwd')
            self.user[role].save()
            self.client[role] = Client()
            self.client[role].login(username=self.user[role].username,
                                    password='pwd')

        self.coll = Collection(
            owner=self.user['owner'],
            name="Test %s" % self.uniqid()
        )
        self.coll.save()
        self.coll.contributors.add(self.user['contrib'])

    def uniqid(self):
        return str(uuid4())[:8]

    def testCollectionSharing(self):
        #view_url = self.coll.get_absolute_url()
        edit_url = reverse('edit_collection',kwargs={'cid': self.coll.pk})
        resp = {}

        for role in ['owner','contrib','someguy']:
            resp[role] = self.client[role].get(edit_url, follow=True)

        """
        assert that owner and contributor can edit the collection,
        and that some guy cannot:
        """
        self.assertEqual(resp['owner'].status_code,200)
        self.assertEqual(resp['contrib'].status_code,200)
        self.assertEqual(resp['someguy'].status_code,403)

        """
        assert that only the owner can view/edit contributors:
        """
        self.assertTrue('contributor' in resp['owner'].content.lower())
        self.assertFalse('contributor' in resp['contrib'].content.lower())


class Afni4DTest(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        app_path = os.path.abspath(os.path.dirname(__file__))
        self.afni_file = os.path.join(app_path,'test_data/TTatlas.nii.gz')
        self.nii_file = os.path.abspath(os.path.join(app_path,'../static/anatomical/MNI152.nii.gz'))

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
