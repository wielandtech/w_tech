from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from unittest.mock import patch
from .models import Action
from .utils import create_action


class ActionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')

    def test_create_action_model(self):
        action = Action.objects.create(user=self.user, verb='test action')
        self.assertEqual(action.user, self.user)
        self.assertEqual(action.verb, 'test action')
        self.assertIsNone(action.target)
        self.assertIsNotNone(action.created)


class CreateActionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='actionuser', password='pass')

    def test_create_action_without_target(self):
        created = create_action(self.user, 'did something')
        self.assertTrue(created)
        self.assertEqual(Action.objects.count(), 1)

    def test_prevent_duplicate_action_within_60_seconds(self):
        create_action(self.user, 'clicked button')
        # Try to create the same action again
        second = create_action(self.user, 'clicked button')
        self.assertFalse(second)
        self.assertEqual(Action.objects.count(), 1)

    def test_create_action_with_target(self):
        # Create a dummy target model instance (using User as target for test)
        target = User.objects.create_user(username='targetuser', password='pass')
        created = create_action(self.user, 'followed', target=target)
        self.assertTrue(created)

        action = Action.objects.first()
        self.assertEqual(action.target, target)
        self.assertEqual(action.target_ct, ContentType.objects.get_for_model(target))
        self.assertEqual(action.target_id, target.id)

    @patch('actions.utils.Action.save')
    def test_create_action_save_called(self, mock_save):
        create_action(self.user, 'patched action')
        mock_save.assert_called_once()
