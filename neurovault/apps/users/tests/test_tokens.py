from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

UserModel = get_user_model()

class BaseTest(TestCase):
    def setUp(self):
        self.user_password = "random"
        self.user = UserModel.objects.create_user(
            "neurouser", "neurouser@example.com", self.user_password
        )

    def tearDown(self):
        self.user.delete()

class TokenGenerationTest(BaseTest):
    def test_token_list(self):
        self.client.login(username=self.user.username, password=self.user_password)
        response = self.client.get(reverse('users:token_list'))
        self.assertEqual(response.status_code, 200)

    def test_token_list_unauthorized(self):
        response = self.client.get(reverse('users:token_list'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/accounts/login/?next=/accounts/token/")

    def test_token_create(self):
        self.client.login(username=self.user.username, password=self.user_password)
        token = Token.objects.filter(user=self.user).first()
        self.assertIsNone(token)

        response = self.client.get(reverse('users:token_list'))
        token = Token.objects.filter(user=self.user).first()
        self.assertIsNotNone(Token)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('users:token_create'))
        new_token = Token.objects.filter(user=self.user).first()
        self.assertNotEqual(token, new_token)

    def test_token_create_unauthorized(self):
        response = self.client.post(reverse('users:token_create'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/accounts/login/?next=/accounts/token/new")

        
    def test_token_auth(self):
        self.client.login(username=self.user.username, password=self.user_password)
        self.client.get(reverse('users:token_list'))
        token = Token.objects.filter(user=self.user).first()

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        post_dict = {
            "name": "Test Create Collection",
        }
        response = client.post("/api/collections/", post_dict)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], post_dict["name"])
