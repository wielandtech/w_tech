from django.test import SimpleTestCase
from core.sitemaps import StaticViewSitemap


class StaticViewSitemapTests(SimpleTestCase):
    def setUp(self):
        self.sitemap = StaticViewSitemap()

    def test_items(self):
        self.assertEqual(self.sitemap.items(), ['core:homepage'])

    def test_location(self):
        self.assertEqual(self.sitemap.location('core:homepage'), '/')
