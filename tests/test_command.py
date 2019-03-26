from unittest import TestCase
import tempfile
import subprocess


class CachedCommandTestCase(TestCase):
    def test_run_and_cache(self):
        with tempfile.TemporaryDirectory() as tmpd:
            command = [
                # intentionally skiping input fd to provide a way for checking if cache works
                'bin/cached', '-d', tmpd, '-o1', 'cat',
            ]
            run_kwargs = dict(
                stdout=subprocess.PIPE,
                check=True,
            )
            completed1 = subprocess.run(
                command,
                input=b'run 1',
                **run_kwargs,
            )
            self.assertEqual(completed1.stdout, b'run 1')
            completed2 = subprocess.run(
                command,
                input=b'run 2',
                **run_kwargs,
            )
            self.assertEqual(completed2.stdout, b'run 1')
