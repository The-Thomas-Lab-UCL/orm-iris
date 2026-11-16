"""Storage warnings and narrowly scoped manual recovery cleanup."""
from pathlib import Path
import os
import re
import shutil
import stat


GIB = 2**30
LOW_FREE_BYTES = 10 * GIB
LOW_FREE_FRACTION = .05
LOCK_NAME = '.iris-recovery.lock'
RUN_PREFIXES = ('mapping_recovery_', 'integration_experiment_', 'laser_power_experiment_', 'single_acquisition_')
KNOWN_FILES = {'settings.json', 'maps.pkl', 'maps.tmp', 'pending_results.pkl', 'remaining_coordinates.json',
               'power_readbacks.jsonl', 'laser_monitor.jsonl', 'laser_quality.json',
               'scan_timing.csv', 'scan_timing.json', 'scan_timing.txt', 'z_surface_tracking.json', LOCK_NAME}
JOURNAL_NAME = re.compile(r'recovery_[0-9a-f]{32}\.iris-autosave(?:-journal|-wal|-shm)?\Z')


def disk_capacity(folder):
    path = Path(folder).resolve()
    while not path.exists() and path != path.parent:
        path = path.parent
    usage = shutil.disk_usage(path)
    return dict(free_bytes=usage.free, total_bytes=usage.total,
                low_space=usage.free < max(LOW_FREE_BYTES, usage.total * LOW_FREE_FRACTION))


class RunLease:
    """Cross-process advisory lock; released by the OS if IRIS crashes."""
    def __init__(self, folder, create=True):
        path = Path(folder) / LOCK_NAME
        self.stream = path.open('a+b' if create else 'r+b')
        try:
            if path.stat().st_size == 0:
                self.stream.write(b'0')
                self.stream.flush()
            self.stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            self.stream.close()
            raise

    def close(self):
        if self.stream is None:
            return
        try:
            self.stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        finally:
            self.stream.close()
            self.stream = None


def _linked(path):
    value = path.lstat()
    return stat.S_ISLNK(value.st_mode) or bool(getattr(value, 'st_file_attributes', 0) & 0x400)


def _target(root, name):
    root = Path(root).resolve(strict=True)
    if not name or name != Path(name).name or not name.startswith(RUN_PREFIXES):
        raise ValueError('Select an IRIS recovery run folder.')
    target = root / name
    if _linked(target) or target.resolve(strict=True).parent != root or not target.is_dir():
        raise ValueError('Recovery target must be an unlinked direct child of the selected data folder.')
    return root, target


def _contents(root, target):
    files, total, modified, anchor = [], 0, target.stat().st_mtime, False
    for path in target.iterdir():
        try:
            if _linked(path) or path.resolve(strict=True).parent != target.resolve():
                raise ValueError('Contains linked files or folders; inspect manually.')
            if not path.is_file() or (path.name not in KNOWN_FILES and not JOURNAL_NAME.fullmatch(path.name)):
                raise ValueError('Contains exports or other files; inspect manually.')
            info = path.stat()
        except FileNotFoundError:
            continue  # A live writer can finish and remove a SQLite rollback journal.
        files.append(path)
        total += info.st_size
        modified = max(modified, info.st_mtime)
        anchor |= path.name in ('settings.json', 'maps.pkl', LOCK_NAME) or bool(JOURNAL_NAME.fullmatch(path.name))
    if not anchor:
        raise ValueError('No recognizable IRIS recovery files found.')
    return files, total, modified


def run_info(root, name, active_paths=()):
    root, target = _target(root, name)
    active_paths = {Path(path).resolve() for path in active_paths}
    files, size, modified = _contents(root, target)
    active = target in active_paths
    lease = None
    if not active and (target / LOCK_NAME).exists():
        try:
            lease = RunLease(target, create=False)
        except OSError:
            active = True
        finally:
            if lease is not None:
                lease.close()
    return dict(name=name, size_bytes=size, modified=modified, active=active,
                deletable=not active, status='Active / finishing' if active else 'Inactive; export not verified')


def list_recovery_runs(root, active_paths=()):
    root = Path(root).resolve()
    if not root.exists():
        return []
    result = []
    for path in root.iterdir():
        if not path.name.startswith(RUN_PREFIXES):
            continue
        try:
            result.append(run_info(root, path.name, active_paths))
        except (OSError, ValueError) as error:
            result.append(dict(name=path.name, size_bytes=None, modified=0, active=False,
                               deletable=False, status=f'Protected: {error}'))
    return sorted(result, key=lambda item: item['modified'], reverse=True)


def delete_recovery_run(root, name, active_paths=()):
    """Delete only whitelisted files in one validated flat run folder.

    The lock remains held while files are removed. No recursive traversal or
    exported file deletion is allowed. Production runs always use unique folders.
    """
    root, target = _target(root, name)
    if target in {Path(path).resolve() for path in active_paths}:
        raise ValueError('This recovery run is still active or finishing.')
    # Check all contents before any mutation, including creating a legacy lock.
    _contents(root, target)
    lease = RunLease(target)
    try:
        files, size, _ = _contents(root, target)
        for path in files:
            if path.name == LOCK_NAME:
                continue
            # Recheck the absolute target before every deletion.
            _target(root, name)
            if _linked(path) or path.resolve(strict=True).parent != target:
                raise ValueError('Recovery contents changed; cleanup stopped.')
            path.unlink()
    finally:
        lease.close()
    (target / LOCK_NAME).unlink()
    target.rmdir()
    return size
