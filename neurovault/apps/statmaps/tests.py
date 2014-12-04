from django.test import TestCase
from django.test import Client
from django.core.urlresolvers import reverse
from neurovault.apps.statmaps.models import Collection,User
from uuid import uuid4


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


