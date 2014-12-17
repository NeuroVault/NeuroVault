from django.test import TestCase, Client, override_settings
from django.core.urlresolvers import reverse
from neurovault.apps.statmaps.models import Collection,User
from uuid import uuid4
import tempfile
import os
import shutil
from neurovault.apps.statmaps.utils import detect_nidm


class NIDMResultsTest(TestCase):

    def setUp(self):
        self.client = {}
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()

        self.client = Client()
        self.client.login(username=self.user)

        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()


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
