from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from oauth2_provider.models import Application

UserModel = get_user_model()


class BaseTest(TestCase):
    def setUp(self):
        self.user_password = 'random'
        self.user = UserModel.objects.create_user("neurouser",
                                                  "neurouser@example.com",
                                                  self.user_password)

    def tearDown(self):
        self.user.delete()


class TestApplicationRegistrationView(BaseTest):

    def test_application_registration_user(self):
        self.client.login(username=self.user.username,
                          password=self.user_password)

        form_data = {
            'name': 'Random App',
            'client_id': 'client_id',
            'client_secret': 'client_secret',
            'client_type': Application.CLIENT_CONFIDENTIAL,
            'redirect_uris': 'http://example.com',
            'authorization_grant_type': Application.GRANT_AUTHORIZATION_CODE
        }

        response = self.client.post(reverse('developerapps_register'),
                                    form_data)
        self.assertEqual(response.status_code, 302)

        app = Application.objects.get(name="Random App")
        self.assertEqual(app.user.username, self.user.username)


class TestApplicationViews(BaseTest):
    def _create_application(self, name, user):
        app = Application.objects.create(
            name=name,
            redirect_uris="http://example.com",
            client_type=Application.CLIENT_CONFIDENTIAL, authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            user=user
        )
        return app

    def setUp(self):
        super(TestApplicationViews, self).setUp()
        self.app = self._create_application('app 1', self.user)

    def tearDown(self):
        super(TestApplicationViews, self).tearDown()
        self.app.delete()

    def test_application_list(self):
        self.client.login(username=self.user.username,
                          password=self.user_password)

        response = self.client.get(reverse('developerapps_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 1)

    def test_application_detail(self):
        self.client.login(username=self.user.username,
                          password=self.user_password)

        response = self.client.get(reverse('developerapps_update',
                                   args=(self.app.pk,)))
        self.assertEqual(response.status_code, 200)

    def test_application_update(self):
        self.client.login(username=self.user.username,
                          password=self.user_password)

        form_data = {
            'name': 'Changed App',
            'client_id': 'client_id',
            'client_secret': 'client_secret',
            'client_type': Application.CLIENT_CONFIDENTIAL,
            'redirect_uris': 'http://example.com',
            'authorization_grant_type': Application.GRANT_AUTHORIZATION_CODE
        }

        response = self.client.post(reverse('developerapps_update',
                                    args=(self.app.pk,)),
                                    form_data)
        self.assertEqual(response.status_code, 302)

        app = Application.objects.get(name="Changed App")
        self.assertEqual(app.user.username, self.user.username)
