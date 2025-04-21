from unittest import mock, TestCase
from core.redis_client import RedisClient


class RedisClientTests(TestCase):
    @mock.patch('core.redis_client.settings')
    @mock.patch('core.redis_client.Redis')
    def test_get_instance_creates_singleton(self, mock_redis_class, mock_settings):
        mock_settings.REDIS_HOST = 'localhost'
        mock_settings.REDIS_PORT = 6379
        mock_settings.REDIS_DB = 0

        instance1 = RedisClient.get_instance()
        instance2 = RedisClient.get_instance()

        self.assertIs(instance1, instance2)
        mock_redis_class.assert_called_once_with(
            host='localhost', port=6379, db=0, decode_responses=True
        )
