import uuid

from django.contrib.auth.models import User

from rest_framework.test import APITestCase
from rest_framework import status

from neurovault.apps.statmaps.models import Collection


class TestCollection(APITestCase):
    def setUp(self):
        self.user_password = 'apitest'
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()

        self.item_url = '/api/collections/%s/' % self.coll.id

    def test_fetch_collection_list(self):
        response = self.client.get('/api/collections/', follow=True)
        self.assertEqual(response.data['results'][0]['echo_time'], None)
        self.assertEqual(response.data['results'][0]['id'], self.coll.id)
        self.assertEqual(response.data['results'][0]['name'], self.coll.name)

    def test_fetch_collection(self):
        response = self.client.get('/api/collections/%s/' % self.coll.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.coll.id)
        self.assertEqual(response.data['name'], self.coll.name)

    def test_create_collection(self):
        self.client.force_authenticate(user=self.user)

        post_dict = {
            'name': 'Test Create Collection',
        }

        response = self.client.post('/api/collections/', post_dict)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], post_dict['name'])

    def test_create_collection_with_doi(self):
        self.client.force_authenticate(user=self.user)

        post_dict = {
            'DOI': '10.3389/fninf.2015.00008',
        }

        response = self.client.post('/api/collections/', post_dict)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['DOI'], post_dict['DOI'])

        doi_properties = {
            'name': 'NeuroVault.org: a web-based repository for collecting '
                    'and sharing unthresholded statistical maps '
                    'of the human brain',
            'authors': 'Krzysztof J. Gorgolewski, Gael Varoquaux, '
                       'Gabriel Rivera, Yannick Schwarz, Satrajit S. Ghosh, '
                       'Camille Maumet, Vanessa V. Sochat, '
                       'Thomas E. Nichols, Russell A. Poldrack, '
                       'Jean-Baptiste Poline, Tal Yarkoni '
                       'and Daniel S. Margulies',
            'paper_url': 'http://journal.frontiersin.org/article'
                         '/10.3389/fninf.2015.00008/abstract',
            'journal_name': 'Frontiers in Neuroinformatics',
            'DOI': post_dict['DOI']
        }

        collection = Collection.objects.get(pk=response.data['id'])

        for key in doi_properties.keys():
            self.assertEqual(response.data[key], doi_properties[key])
            self.assertEqual(getattr(collection, key), doi_properties[key])

    def test_create_collection_with_incorrect_doi(self):
        self.client.force_authenticate(user=self.user)

        post_dict = {
            'DOI': '-*-INCORRECT*-',
        }

        response = self.client.post('/api/collections/', post_dict)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data, {'non_field_errors': ['Could not resolve DOI']}
        )

    def test_missing_required_authentication(self):
        url = '/api/collections/%s/' % self.coll.id

        response = self.client.post(url, {'name': 'failed test'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data, {
            'detail': 'Authentication credentials were not provided.'
        })

    def test_partial_update_collection(self):
        self.client.force_authenticate(user=self.user)

        patch_dict = {
            'description': "renamed %s" % uuid.uuid4(),
        }

        response = self.client.patch(self.item_url, patch_dict)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'],
                         patch_dict['description'])

    def test_update_collection(self):
        self.client.force_authenticate(user=self.user)

        put_dict = {
            'name': "renamed %s" % uuid.uuid4(),
            'description': "renamed %s" % uuid.uuid4(),
        }

        response = self.client.put(self.item_url, put_dict)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'],
                         put_dict['description'])
        self.assertEqual(response.data['name'],
                         put_dict['name'])

    def test_destroy_collection(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.item_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(Collection.DoesNotExist):
            Collection.objects.get(pk=self.coll.pk)

    def test_missing_required_permissions(self):
        self.client.force_authenticate(user=self.user)

        other_user = User.objects.create_user('OtherGuy')
        other_user.save()

        other_collection = Collection(owner=other_user,
                                      name="Another Test Collection")
        other_collection.save()

        url = '/api/collections/%s/' % other_collection.pk

        put_dict = {
            'name': "renamed %s" % uuid.uuid4()
        }

        response = self.client.put(url, put_dict)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, {
            'detail': 'You do not have permission to perform this action.'
        })

    def test_collections_datatable(self):
        url = '/api/collections/%d/datatable/' % self.coll.pk
        response = self.client.get(url, follow=True)

        aa_data = response.data['aaData']

        self.assertIsInstance(aa_data, list)
        key_map = dict(aa_data)

        self.assertEqual(key_map['name'], self.coll.name)
        self.assertEqual(key_map['id'], self.coll.pk)
