from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock
from .models import Image
from .forms import ImageCreateForm, ImageUploadForm
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


class ImageModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='pass')

    def test_slug_is_generated_on_save(self):
        img = Image.objects.create(user=self.user, title='Test Image', url='http://example.com/test.jpg', image='test.jpg')
        self.assertEqual(img.slug, 'test-image')

    def test_get_absolute_url(self):
        img = Image.objects.create(user=self.user, title='Test', url='http://example.com/test.jpg', image='test.jpg')
        self.assertIn(str(img.id), img.get_absolute_url())
        self.assertIn(img.slug, img.get_absolute_url())


class ImageFormTests(TestCase):
    def test_image_create_form_valid(self):
        form = ImageCreateForm(data={'title': 'Test', 'url': 'http://example.com/image.jpg', 'description': 'desc'})
        self.assertTrue(form.is_valid())

    def test_image_create_form_invalid_extension(self):
        form = ImageCreateForm(data={'title': 'Test', 'url': 'http://example.com/image.txt', 'description': 'desc'})
        self.assertFalse(form.is_valid())

    def test_image_upload_form_mutual_exclusion(self):
        form = ImageUploadForm(data={'title': 'Test', 'description': 'desc'})
        self.assertFalse(form.is_valid())

    def test_image_upload_form_valid_upload(self):
        image_file = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")
        form = ImageUploadForm(data={'title': 'Test', 'description': 'desc'}, files={'image': image_file})
        self.assertTrue(form.is_valid())


class ImageViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user1', password='pass')
        self.image = Image.objects.create(user=self.user, title='Title', url='http://example.com/test.jpg', image='test.jpg')

    def test_image_detail_view(self):
        url = reverse('images:detail', args=[self.image.id, self.image.slug])
        with patch('images.views.get_redis') as mock_redis:
            mock_redis.return_value = MagicMock()
            self.client.force_login(self.user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Title')

    def test_image_like_view(self):
        url = reverse('images:like')
        self.client.force_login(self.user)
        response = self.client.post(url, {'id': self.image.id, 'action': 'like'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'ok'})

    def test_image_create_view_get(self):
        url = reverse('images:create')
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_image_upload_view_get(self):
        url = reverse('images:upload')
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
