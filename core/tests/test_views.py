from django.test import TestCase
from django.urls import reverse


class HomepageViewTests(TestCase):
    def test_homepage_status_code(self):
        response = self.client.get(reverse('core:core_home'))
        self.assertEqual(response.status_code, 200)

    def test_homepage_template_used(self):
        response = self.client.get(reverse('core:core_home'))
        self.assertTemplateUsed(response, 'core/index.html')
