from django.contrib.auth.models import User

from rest_framework.test import APITestCase
from rest_framework import status


class TestAuthenticatedUser(APITestCase):
    def setUp(self):
        self.user_fields = {
            'username': 'NeuroGuy',
            'email': 'neuroguy@example.com',
            'first_name': 'Neuro',
            'last_name': 'Guy'
        }
        self.user = User.objects.create_user(**self.user_fields)
        self.user.save()

    def test_unauthenticated_user(self):
        response = self.client.get('/api/user/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data, {
            'detail': 'Authentication credentials were not provided.'
        })

    def test_authenticated_user(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/user/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data['id'], int)

        for field in list(self.user_fields.keys()):
            self.assertEqual(response.data[field], self.user_fields[field])
