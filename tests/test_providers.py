from unittest import TestCase
import tempfile

from cached.providers.fs import FSProcessCache


class InMemoryProcessCacheTestCase(TestCase):
    def test_load_missing(self):
        with tempfile.TemporaryDirectory() as tmpd:
            self.assertIsNone(
                FSProcessCache(tmpd).load_cached(b'a', [b'b', b'c'], {1: b'd', 2: b'e'}),
            )

    def test_store_then_load(self):
        with tempfile.TemporaryDirectory() as tmpd:
            FSProcessCache(tmpd).store_cached(b'a', [b'b', b'c'], {1: b'd', 2: b'e'}, {0: b'f', 1: b'\0\0'})
            self.assertEqual(
                FSProcessCache(tmpd).load_cached(b'a', [b'b', b'c'], {1: b'd', 2: b'e'}),
                {0: b'f', 1: b'\0\0'},
            )

    def test_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpd:
            FSProcessCache(tmpd).store_cached(b'a', [], {}, {0: b'f'})
            FSProcessCache(tmpd).store_cached(b'a', [], {}, {0: b'g'})
            self.assertEqual(
                FSProcessCache(tmpd).load_cached(b'a', [], {}),
                {0: b'g'},
            )
