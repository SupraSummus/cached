import logging
import os
import threading
import hashlib


logger = logging.getLogger(__name__)


# copied from pgspawn - maybe it's time to make library for easy process spawning, more robust than subprocess?
def apply_fd_mapping(fd_mapping):
    """ Takes dict target fd -> present fd. Moves fds to match the mapping. """

    def _dup_mapping(fd, new_fd):
        logger.debug("fd {} duped to {}".format(fd, new_fd))
        for target_fd in fd_mapping.keys():
            if fd_mapping[target_fd] == fd:
                fd_mapping[target_fd] = new_fd

    for target_fd in fd_mapping.keys():
        fd = fd_mapping[target_fd]

        if fd == target_fd:
            # nothing to do
            logger.debug("fd {} already in place".format(fd))
            continue

        # if needed make target fd free
        if target_fd in fd_mapping.values():
            saved_fd = os.dup(target_fd)
            _dup_mapping(target_fd, saved_fd)

        os.dup2(fd, target_fd, inheritable=False)
        _dup_mapping(fd, target_fd)


class WriteAllThenCloseThread(threading.Thread):
    def __init__(self, fd, data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fd = fd
        self.data = data

    def run(self):
        f = os.fdopen(self.fd, 'wb')
        f.write(self.data)
        f.close()
        self.data = None  # release memory


class ReadAllThenCloseThread(threading.Thread):
    def __init__(self, fd, target_dict, key, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fd = fd
        self.target_dict = target_dict
        self.key = key

    def run(self):
        f = os.fdopen(self.fd, 'rb')
        self.target_dict[self.key] = f.read()
        f.close()


def write_and_close_fds(data_dict):
    threads = [
        WriteAllThenCloseThread(fd, data)
        for fd, data in data_dict.items()
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def read_and_close_fds(fds):
    data = {}
    threads = [
        ReadAllThenCloseThread(fd, data, fd)
        for fd in fds
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return data


class ProcessCache:
    def load_cached(self, command, argv, input_hashes):
        """Return dict fd -> bytes cached from earlier run, or None on cache miss"""
        raise NotImplementedError()

    def store_cached(self, command, argv, input_hashes, output_data):
        """Store command run in cache"""
        raise NotImplementedError()

    def input_digest(self, d):
        return hashlib.sha256(d).digest()

    def run(self, command, argv, input_fds, output_fds):
        input_data = read_and_close_fds(input_fds)
        output_data = self.run_cached(command, argv, input_data=input_data, output_fds=output_fds)
        write_and_close_fds(output_data)

    def run_cached(self, command, argv, input_data, output_fds):
        input_hashes = {
            fd: self.input_digest(d)
            for fd, d in input_data.items()
        }
        output_data = self.load_cached(command, argv, input_hashes)
        if output_data is None:
            output_data = self.run_real(command, argv, input_data, output_fds)
            self.store_cached(command, argv, input_hashes, output_data)
        return output_data

    def run_real(self, command, argv, input_data, output_fds):
        fd_mapping = {}  # child fd -> parent fd
        output_data = {}  # child fd -> data
        threads = []

        for subprocess_fd, d in input_data.items():
            reading_end, writing_end = os.pipe()
            assert(subprocess_fd not in fd_mapping)
            fd_mapping[subprocess_fd] = reading_end
            threads.append(WriteAllThenCloseThread(writing_end, d))

        for subprocess_fd in output_fds:
            reading_end, writing_end = os.pipe()
            assert(subprocess_fd not in fd_mapping)
            fd_mapping[subprocess_fd] = writing_end
            threads.append(ReadAllThenCloseThread(reading_end, output_data, subprocess_fd))

        for t in threads:
            t.start()

        pid = os.fork()
        if pid == 0:  # child
            # prepare fds
            apply_fd_mapping(fd_mapping)
            for fd in fd_mapping.keys():
                os.set_inheritable(fd, True)

            # run target executable
            os.execvp(command, argv)
            assert False

        # parent
        for fd in fd_mapping.values():
            os.close(fd)
        os.waitpid(pid, 0)
        for t in threads:
            t.join()

        return output_data


class InMemoryProcessCache(ProcessCache):
    def __init__(self):
        super().__init__()
        self.cache = {}

    def cache_key(self, command, argv, input_hashes):
        return (
            command,
            tuple(argv),
            tuple(sorted(input_hashes.items())),
        )

    def load_cached(self, command, argv, input_hashes):
        return self.cache.get(self.cache_key(command, argv, input_hashes))

    def store_cached(self, command, argv, input_hashes, output_data):
        self.cache[self.cache_key(command, argv, input_hashes)] = output_data
