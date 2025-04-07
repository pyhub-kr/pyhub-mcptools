from time import sleep

import pytest
from django.core.cache import caches
from django.test import TestCase


class BaseCacheTest:
    """캐시 테스트를 위한 기본 테스트 케이스"""

    @pytest.fixture(autouse=True)
    def setup_cache(self):
        self.cache_backend = self.get_cache_backend()

    def get_cache_backend(self):
        """하위 클래스에서 구현해야 하는 메서드"""
        raise NotImplementedError

    def test_cache_set_and_get(self):
        # 캐시 동작 테스트
        self.cache_backend.set("test_key", "test_value", 30)  # 30초 TTL
        self.assertEqual(self.cache_backend.get("test_key"), "test_value")

    def test_cache_delete(self):
        # 캐시 삭제 테스트
        self.cache_backend.set("test_key", "test_value")
        self.cache_backend.delete("test_key")
        self.assertIsNone(self.cache_backend.get("test_key"))

    def test_cache_timeout(self):
        # 짧은 TTL로 만료 테스트
        self.cache_backend.set("test_key", "test_value", 1)  # 1초 TTL
        self.assertEqual(self.cache_backend.get("test_key"), "test_value")
        sleep(1.1)  # TTL 초과 대기
        self.assertIsNone(self.cache_backend.get("test_key"))

    def test_cache_default_value(self):
        # 존재하지 않는 키에 대한 기본값 테스트
        self.assertEqual(self.cache_backend.get("nonexistent_key", "default_value"), "default_value")


class DefaultCacheTest(BaseCacheTest, TestCase):
    def get_cache_backend(self):
        return caches["default"]


class LocmemCacheTest(BaseCacheTest, TestCase):
    def get_cache_backend(self):
        return caches["locmem"]
