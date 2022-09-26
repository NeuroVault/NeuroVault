from django.test import TestCase, Client
from django.http import HttpResponse
from django.urls import reverse, re_path, include

from django.contrib.auth import get_user_model

from rest_framework import permissions
from rest_framework.views import APIView
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

UserModel = get_user_model()


class MockView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return HttpResponse({'a': 1, 'b': 2, 'c': 3})


class OAuth2View(MockView):
    authentication_classes = [OAuth2Authentication]


urlpatterns = [
    re_path(r'^oauth2/', include('oauth2_provider.urls')),
    re_path(r'^oauth2-test/$', OAuth2View.as_view()),
    re_path(r'^accounts/', include('neurovault.apps.users.urls')),

]


class TestPersonalAccessTokens(TestCase):
    urls = 'neurovault.apps.users.tests.test_oauth'

    def setUp(self):
        self.user_password = "l0n6 l1v3 7h3 k1n6!"
        self.user = UserModel.objects.create_user("bernardo",
                                                  "bernardo@example.com",
                                                  self.user_password)
        self.client = Client()

    def tearDown(self):
        self.user.delete()

    def _create_authorization_header(self, token):
        return "Bearer {0}".format(token)

    def test_authentication_empty(self):
        response = self.client.get("/oauth2-test/")
        self.assertEqual(response.status_code, 401)

    def test_authentication_denied(self):
        auth = self._create_authorization_header("fake-token")
        response = self.client.get("/oauth2-test/", HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 401)

    def test_authentication_allow(self):
        self.client.login(username=self.user, password=self.user_password)
        response = self.client.post(reverse('token_create'))
        self.assertEqual(response.status_code, 302)

        access_token = self.user.accesstoken_set.first()

        auth = self._create_authorization_header(access_token)
        response = self.client.get("/oauth2-test/", HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)
