import os
import tempfile
import shutil
import hashlib

from cached import ProcessCache


class FSProcessCache(ProcessCache):
    def __init__(self, dir_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dir_path = dir_path

    def entry_dir_path(self, command, argv, input_hashes):
        total_hash = hashlib.sha256()
        total_hash.update(command)
        total_hash.update(b'\0')
        total_hash.update(str(len(argv)).encode('ascii'))
        total_hash.update(b'\0')
        for arg in argv:
            total_hash.update(arg)
            total_hash.update(b'\0')
        for fd, h in input_hashes.items():
            total_hash.update(str(fd).encode('ascii'))
            total_hash.update(b'\0')
            total_hash.update(h)
        return os.path.join(self.dir_path, total_hash.hexdigest())

    def load_cached(self, command, argv, input_hashes):
        dir_path = self.entry_dir_path(command, argv, input_hashes)
        if not os.path.exists(dir_path):
            return None
        r = {}
        for filename in os.listdir(dir_path):
            fd = int(filename)
            with open(os.path.join(dir_path, filename), 'rb') as f:
                r[fd] = f.read()
        return r

    def store_cached(self, command, argv, input_hashes, output_data):
        d = tempfile.mkdtemp(dir=self.dir_path)
        for fd, data in output_data.items():
            with open(os.path.join(d, str(fd)), 'wb') as f:
                f.write(data)
        dir_path = self.entry_dir_path(command, argv, input_hashes)
        if os.path.exists(dir_path):
            self.atomic_delete(dir_path)
        os.rename(d, dir_path)

    def atomic_delete(self, directory):
        tmp = tempfile.mkdtemp(dir=os.path.dirname(directory))
        os.rmdir(tmp)
        os.rename(directory, tmp)
        shutil.rmtree(tmp)
