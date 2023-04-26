from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase
from django.test import TestCase
from django.contrib.auth.models import User

from .test_application_views import BaseTest

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

        
