from unittest import TestCase
from cached import InMemoryProcessCache


class InMemoryProcessCacheTestCase(TestCase):
    def test_cache_miss(self):
        c = InMemoryProcessCache()
        self.assertIsNone(c.load_cached('echo', ['echo', 'aaa'], {}))

    def test_cache_hit(self):
        c = InMemoryProcessCache()
        c.run_cached('echo', ['echo', 'aaa'], {}, [1])
        self.assertEqual(c.load_cached('echo', ['echo', 'aaa'], {}), {1: b'aaa\n'})

    def test_input_cache_miss(self):
        c = InMemoryProcessCache()
        c.run_cached('cat', ['cat'], {0: b'aaa'}, [1])
        self.assertIsNone(c.load_cached('cat', ['cat'], {0: b'bbb'}))

    def test_input_cache_hit(self):
        c = InMemoryProcessCache()
        c.run_cached('cat', ['cat'], {0: b'aaa'}, [1])
        self.assertEqual(
            c.load_cached('cat', ['cat'], {0: c.input_digest(b'aaa')}),
            {1: b'aaa'},
        )
