from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Profile, Contact
from .forms import LoginForm, UserRegistrationForm
from .authentication import EmailAuthBackend


class UserModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='alice', email='alice@example.com', password='password123')
        self.user2 = User.objects.create_user(username='bob', email='bob@example.com', password='password123')
        self.profile1 = Profile.objects.create(user=self.user1)

    def test_profile_str(self):
        self.assertEqual(str(self.profile1), 'Profile for user alice')

    def test_following_relationship(self):
        Contact.objects.create(user_from=self.user1, user_to=self.user2)
        self.assertIn(self.user2, self.user1.following.all())
        self.assertIn(self.user1, self.user2.followers.all())


class AuthBackendTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='jane', email='jane@example.com', password='12345')

    def test_authenticate_with_valid_email(self):
        backend = EmailAuthBackend()
        user = backend.authenticate(None, username='jane@example.com', password='12345')
        self.assertEqual(user, self.user)

    def test_authenticate_with_invalid_email(self):
        backend = EmailAuthBackend()
        user = backend.authenticate(None, username='fake@example.com', password='12345')
        self.assertIsNone(user)


class FormTests(TestCase):
    def test_login_form_valid(self):
        form = LoginForm(data={'username': 'test', 'password': 'pass'})
        self.assertTrue(form.is_valid())

    def test_user_registration_password_mismatch(self):
        form = UserRegistrationForm(data={
            'username': 'newuser',
            'first_name': 'New',
            'email': 'new@example.com',
            'password': 'abc123',
            'password2': 'def456'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('Passwords don\'t match.', form.errors['password2'])


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='dave', email='dave@example.com', password='secret123')
        self.profile = Profile.objects.create(user=self.user)

    def test_register_view(self):
        response = self.client.post(reverse('account:register'), {
            'username': 'newuser',
            'first_name': 'New',
            'email': 'new@example.com',
            'password': 'testpass123',
            'password2': 'testpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_edit_view_requires_login(self):
        response = self.client.get(reverse('account:edit'))
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_dashboard_view_logged_in(self):
        self.client.login(username='dave', password='secret123')
        response = self.client.get(reverse('account:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_follow_and_unfollow_user(self):
        self.client.login(username='dave', password='secret123')
        other = User.objects.create_user(username='eve', password='abc123')

        follow = self.client.post(reverse('account:user_follow'), {'id': other.id, 'action': 'follow'},
                                  HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertJSONEqual(follow.content, {'status': 'ok'})

        unfollow = self.client.post(reverse('account:user_follow'), {'id': other.id, 'action': 'unfollow'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertJSONEqual(unfollow.content, {'status': 'ok'})
