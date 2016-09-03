import json
import nibabel
import os
import shutil
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import TestCase, Client, override_settings, RequestFactory
from uuid import uuid4

from neurovault.apps.statmaps.models import Collection, User, Image, Atlas
from neurovault.apps.statmaps.utils import detect_4D, split_4D_to_3D
from neurovault.apps.statmaps.views import delete_collection
from neurovault.settings import PRIVATE_MEDIA_ROOT
from .utils import clearDB, save_statmap_form


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
        self.coll.save()

    def uniqid(self):
        return str(uuid4())[:8]

    @override_settings(CRISPY_FAIL_SILENTLY=False)
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


class DeleteCollectionsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.test_path = os.path.abspath(os.path.dirname(__file__))
        self.user = User.objects.create(username='neurovault')
        self.client = Client()
        self.client.login(username=self.user)
        self.Collection1 = Collection(name='Collection1',owner=self.user)
        self.Collection1.save()
        self.unorderedAtlas = Atlas(name='unorderedAtlas', description='',collection=self.Collection1)
        self.unorderedAtlas.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        self.unorderedAtlas.label_description_file = SimpleUploadedFile('test_VentralFrontal_thr75_summaryimage_2mm.xml', file(os.path.join(self.test_path,'test_data/api/unordered_VentralFrontal_thr75_summaryimage_2mm.xml')).read())
        self.unorderedAtlas.save()

        self.Collection2 = Collection(name='Collection2',owner=self.user)
        self.Collection2.save()
        self.orderedAtlas = Atlas(name='orderedAtlas', collection=self.Collection2, label_description_file='VentralFrontal_thr75_summaryimage_2mm.xml')
        self.orderedAtlas.file = SimpleUploadedFile('VentralFrontal_thr75_summaryimage_2mm.nii.gz', file(os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.nii.gz')).read())
        self.orderedAtlas.label_description_file = SimpleUploadedFile('test_VentralFrontal_thr75_summaryimage_2mm.xml', file(os.path.join(self.test_path,'test_data/api/VentralFrontal_thr75_summaryimage_2mm.xml')).read())
        self.orderedAtlas.save()

    def tearDown(self):
        clearDB()

    def testDeleteCollection(self):
        self.client.login(username=self.user)
        pk1 = self.Collection1.pk
        pk2 = self.Collection2.pk
        request = self.factory.get('/collections/%s/delete' %pk1)
        request.user = self.user
        delete_collection(request, str(pk1))
        imageDir = os.path.join(PRIVATE_MEDIA_ROOT, 'images')
        dirList = os.listdir(imageDir)
        print dirList
        self.assertIn(str(self.Collection2.pk), dirList)
        self.assertNotIn(str(self.Collection1.pk), dirList)



class Afni4DTest(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        app_path = os.path.abspath(os.path.dirname(__file__))
        self.afni_file = os.path.join(app_path,'test_data/TTatlas.nii.gz')
        self.nii_file = os.path.abspath(os.path.join(app_path,'../static/anatomical/MNI152.nii.gz'))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        clearDB()

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
        test_afni = detect_4D(nibabel.load(self.afni_file))
        test_non_afni = detect_4D(nibabel.load(self.nii_file))

        bricks = split_4D_to_3D(nibabel.load(self.afni_file),tmp_dir=self.tmpdir)

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


class CollectionMetaDataTest(TestCase):

    def setUp(self):
        base_username = 'owner'
        password = 'pwd'
        test_path = os.path.abspath(os.path.dirname(__file__))

        self.user = User.objects.create_user(
            "%s_%s" % (base_username, self.uniqid()), None, password
        )
        self.user.save()

        self.client = Client()
        self.client.login(username=self.user.username, password=password)

        self.coll = Collection(owner=self.user,
                               name="Test %s" % self.uniqid())
        self.coll.save()

        def test_data_path(filename):
            return os.path.join(test_path, 'test_data/statmaps/%s' % filename)

        self.image1 = save_statmap_form(
            image_path=test_data_path('motor_lips.nii.gz'),
            collection=self.coll
        )
        self.image2 = save_statmap_form(
            image_path=test_data_path('beta_0001.nii.gz'),
            collection=self.coll
        )

    def tearDown(self):
        clearDB()

    def uniqid(self):
        return str(uuid4())[:8]

    def test_post_metadata(self):
        cognitive_paradigms = ('Early Social and Communication Scales',
                               'Cambridge Gambling Task')

        test_data = [
            ['Filename', 'Subject ID', 'Sex', 'modality',
                'cognitive_paradigm_cogatlas'],
            ['motor_lips.nii.gz', '12', '1',
                'fMRI-BOLD', cognitive_paradigms[0]],
            ['beta_0001.nii.gz', '13', '2',
                'fMRI-BOLD', cognitive_paradigms[1]]
        ]

        url = reverse('edit_metadata',
                      kwargs={'collection_cid': self.coll.pk})

        resp = self.client.post(url,
                                data=json.dumps(test_data),
                                content_type='application/json; charset=utf-8')

        self.assertEqual(resp.status_code, 200)

        image1 = Image.objects.get(id=self.image1.id)

        self.assertEqual(image1.data, {'Sex': '1',
                                       'Subject ID': '12'})

        self.assertEqual(image1.modality, 'fMRI-BOLD')
        self.assertEqual(image1.cognitive_paradigm_cogatlas.name,
                         cognitive_paradigms[0])

        image2 = Image.objects.get(id=self.image2.id)

        self.assertEqual(image2.cognitive_paradigm_cogatlas.name,
                         cognitive_paradigms[1])

    def test_empty_string_value_in_fixed_numeric_field(self):
        test_data = [
            ['Filename', 'Subject ID', 'number_of_subjects'],
            ['motor_lips.nii.gz', '12', ''],
            ['beta_0001.nii.gz', '13', None]
        ]

        url = reverse('edit_metadata',
                      kwargs={'collection_cid': self.coll.pk})

        resp = self.client.post(url,
                                data=json.dumps(test_data),
                                content_type='application/json; charset=utf-8')

        self.assertEqual(resp.status_code, 200)

        image1 = Image.objects.get(id=self.image1.id)
        self.assertIsNone(image1.number_of_subjects)

        image2 = Image.objects.get(id=self.image2.id)
        self.assertIsNone(image2.number_of_subjects)

    def test_metadata_for_files_missing_in_the_collection(self):
        test_data = [
            ['Filename', 'Subject ID', 'Sex'],
            ['motor_lips.nii.gz', '12', '1'],
            ['beta_0001.nii.gz', '13', '2'],
            ['file3.nii.gz', '14', '3']
        ]

        url = reverse('edit_metadata',
                      kwargs={'collection_cid': self.coll.pk})

        resp = self.client.post(url,
                                data=json.dumps(test_data),
                                content_type='application/json; charset=utf-8')

        self.assertEqual(resp.status_code, 400)

        resp_json = json.loads(resp.content)

        self.assertEqual(resp_json['message'],
                         'File is not found in the collection: file3.nii.gz')

    def test_incorrect_value_in_fixed_basic_field(self):
        test_data = [
            ['Filename', 'Subject ID', 'Sex', 'modality',
                'cognitive_paradigm_cogatlas'],
            ['motor_lips.nii.gz', '12', '1',
                'fMRI-BOLD', 'Cambridge Gambling Task'],
            ['beta_0001.nii.gz', '13', '2',
                '-*NOT-EXISTING-MOD*-', 'Cambridge Gambling Task']
        ]

        url = reverse('edit_metadata',
                      kwargs={'collection_cid': self.coll.pk})

        resp = self.client.post(url,
                                data=json.dumps(test_data),
                                content_type='application/json; charset=utf-8')

        self.assertEqual(resp.status_code, 400)

        resp_json = json.loads(resp.content)

        self.assertEqual(resp_json['messages'], {'beta_0001.nii.gz': [{
            'Modality & acquisition type': [
                "Value '-*NOT-EXISTING-MOD*-' is not a valid choice."
            ]
        }]})

    def test_incorrect_value_in_fixed_foreign_field(self):
        test_data = [
            ["Filename", "Subject ID", "Sex", "modality",
                "cognitive_paradigm_cogatlas"],
            ["motor_lips.nii.gz", "12", "1", "fMRI-BOLD",
                '-*NOT-EXISTING-PARADIGM*-'],
            ["beta_0001.nii.gz", "13", "2",
                "fMRI-BOLD", 'Cambridge Gambling Task']
        ]

        url = reverse('edit_metadata',
                      kwargs={'collection_cid': self.coll.pk})

        resp = self.client.post(url,
                                data=json.dumps(test_data),
                                content_type='application/json; charset=utf-8')

        self.assertEqual(resp.status_code, 400)

        resp_json = json.loads(resp.content)

        self.assertEqual(resp_json['messages'], {'motor_lips.nii.gz': [{
            'Cognitive atlas paradigm': [
                "Value '-*NOT-EXISTING-PARADIGM*-' is not a valid choice."
            ]
        }]})
