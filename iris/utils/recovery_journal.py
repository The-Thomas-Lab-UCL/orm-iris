"""Incremental recovery journals, separate from IRIS's DB/Parquet export format.

Only new, detached measurement data enters the queue. SQLite serialization and
commits run on one background thread. Never unpickle an untrusted journal.
"""
from contextlib import closing
from copy import deepcopy
from pathlib import Path
import pickle
import queue
import sqlite3
import threading
import time
import uuid

from iris.utils.autosave_storage import RunLease, disk_capacity


FORMAT = 'iris-recovery-v1'
COMMIT_INTERVAL_S = 20.0


class RecoveryWriter:
    def __init__(self, folder, settings=None, interval_s=COMMIT_INTERVAL_S, max_pending=4096):
        if max_pending < 1:
            raise ValueError('Autosave queue capacity must be positive.')
        if interval_s <= 0:
            raise ValueError('Autosave interval must be positive.')
        folder = Path(folder).resolve(strict=True)
        if not folder.is_dir():
            raise ValueError('Choose an existing autosave folder.')
        self._run_lease = RunLease(folder)
        self._capacity = {}
        self.path = folder / f'recovery_{uuid.uuid4().hex}.iris-autosave'
        self.interval_s = interval_s
        self._queue = queue.Queue(maxsize=max_pending)
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._accepted = self._committed = 0
        self._last_commit = None
        self._error = None
        self._closed = False
        self._keep_run_lease = False
        self._release_after_start_failure = False
        self._settings = settings or {}
        self.thread = threading.Thread(target=self._run, name='IRIS autosave', daemon=True)
        self.thread.start()
        if not self._ready.wait(10):
            self._release_after_start_failure = True
            self._stop.set()
            if not self.thread.is_alive():
                self.release_run()
            raise TimeoutError('Autosave drive did not respond before the scan started.')
        try:
            self.check()
        except Exception:
            self._release_after_start_failure = True
            self.thread.join(1)
            if not self.thread.is_alive():
                self.release_run()
            raise

    def release_run(self):
        """Called after the final snapshot/timing files, not just journal flush."""
        if self._run_lease is not None:
            self._run_lease.close()
            self._run_lease = None

    @property
    def run_active(self):
        return self._run_lease is not None

    def check(self):
        if self._error is not None:
            raise RuntimeError(f'Autosave failed: {self._error}. Acquired data remains in memory.') from self._error

    def submit(self, unit, timestamp, coordinate, measurement):
        """Detach only this spectrum, never copy or scan the accumulated map."""
        self.check()
        payload = dict(acquisition_kind=self._settings.get('acquisition_kind', 'map'),
                       unit_id=unit.get_unit_id(), unit_name=unit.get_unit_name(),
                       unit_metadata=deepcopy(unit.get_dict_unit_metadata()),
                       timestamp=int(timestamp), coordinate=tuple(float(v) for v in coordinate),
                       metadata=deepcopy(measurement.get_metadata()),
                       raw=[frame.copy(deep=True) for frame in measurement.get_raw_list()],
                       averaged=measurement.get_analysed().copy(deep=True))
        with self._lock:
            if self._closed:
                raise RuntimeError('The autosave writer is already closed.')
            try:
                self._queue.put_nowait(payload)
            except queue.Full:
                raise RuntimeError('Autosave cannot keep up. Scan stopped; data remains in memory.') from None
            self._accepted += 1

    def submit_single_exposure(self, unit, timestamp, spectrum, metadata):
        """Save just the new exposure, without re-copying an expanding accumulation."""
        from iris.data.measurement_Raman import MeaRaman

        measurement = MeaRaman(timestamp=int(timestamp), int_time_ms=metadata['integration_time_ms'],
                               laserPower_mW=metadata['laser_power_milliwatt'],
                               laserWavelength_nm=metadata['laser_wavelength_nm'])
        measurement.set_raw_list(spectrum, timestamp_int=int(timestamp))
        measurement.check_uptodate()
        if unit.get_dict_measurement_metadata() is None:
            unit.set_dict_metadata(dict(unit.get_dict_unit_metadata(), measurement_metadata=measurement.get_metadata()))
        # Standalone spectra have no captured stage coordinate, matching the
        # existing Data Hub's convention for single measurements.
        self.submit(unit, int(timestamp), (0., 0., 0.), measurement)

    def status(self):
        with self._lock:
            return dict(accepted=self._accepted, committed=self._committed,
                        last_commit=self._last_commit, error=str(self._error) if self._error else None,
                        finished=not self.thread.is_alive(), path=str(self.path),
                        run_active=self.run_active, **self._capacity)

    def close(self, timeout=15, *, release_run=None):
        """Flush after acquisition stops, without delaying individual scan points."""
        if release_run is not None:
            self._keep_run_lease = not release_run
        with self._lock:
            self._closed = True
            self._stop.set()
        self.thread.join(timeout)
        if self.thread.is_alive():
            raise TimeoutError('Autosave is still finishing. Wait before starting another scan.')
        try:
            self.check()
        finally:
            if not self._keep_run_lease:
                self.release_run()

    def _commit(self, connection, records):
        if not records:
            return
        self._capacity = disk_capacity(self.path.parent)
        rows = [(item['unit_id'], item['timestamp'], pickle.dumps(item, protocol=5)) for item in records]
        with connection:
            connection.executemany('INSERT INTO spectra(unit_id,timestamp,payload) VALUES (?,?,?)', rows)
        with self._lock:
            self._committed += len(rows)
            self._last_commit = time.time()

    def _run(self):
        connection = None
        try:
            self._capacity = disk_capacity(self.path.parent)
            connection = sqlite3.connect(self.path)
            # One writer and post-scan readers need no WAL shared-memory files.
            connection.execute('PRAGMA journal_mode=DELETE')
            connection.execute('PRAGMA synchronous=FULL')
            with connection:
                connection.execute('CREATE TABLE info(key TEXT PRIMARY KEY,value BLOB NOT NULL)')
                connection.execute('CREATE TABLE spectra(sequence INTEGER PRIMARY KEY,unit_id TEXT NOT NULL,'
                                   'timestamp INTEGER NOT NULL,payload BLOB NOT NULL,UNIQUE(unit_id,timestamp))')
                connection.executemany('INSERT INTO info VALUES (?,?)',
                                       [('format', FORMAT), ('settings', pickle.dumps(self._settings, protocol=5))])
            self._ready.set()
            pending = []
            deadline = time.monotonic() + self.interval_s
            while True:
                # Bound memory even if a very fast producer outruns the disk.
                if not (self._stop.is_set() and self._queue.empty()):
                    try:
                        pending.append(self._queue.get(timeout=min(.1, max(0, deadline-time.monotonic()))))
                    except queue.Empty:
                        pass
                if time.monotonic() >= deadline or self._stop.is_set():
                    self._commit(connection, pending)
                    pending.clear()
                    deadline = time.monotonic() + self.interval_s
                if self._stop.is_set() and self._queue.empty():
                    break
                if len(pending) >= self._queue.maxsize:
                    self._commit(connection, pending)
                    pending.clear()
                    deadline = time.monotonic() + self.interval_s
        except Exception as error:
            self._error = error
        finally:
            self._ready.set()
            if connection is not None:
                connection.close()
            if self._release_after_start_failure:
                self.release_run()


def read_recovery(path):
    """Read committed rows only. Caller must trust this locally generated file."""
    uri = Path(path).resolve(strict=True).as_uri() + '?mode=rw'
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        marker = connection.execute("SELECT value FROM info WHERE key='format'").fetchone()
        if marker != (FORMAT,):
            raise ValueError('This is not a supported IRIS recovery file.')
        return [pickle.loads(row[0]) for row in connection.execute('SELECT payload FROM spectra ORDER BY sequence')]


def recover_mapping_hub(path):
    """Rebuild ordinary IRIS maps, which the existing .db exporter can save."""
    from iris.data.measurement_Raman import MeaRaman
    from iris.data.measurement_RamanMap import MeaRMap_Hub, MeaRMap_Unit

    hub = MeaRMap_Hub()
    units = {}
    single_measurements = {}
    for record in read_recovery(path):
        unit_id = record['unit_id']
        if record.get('acquisition_kind') == 'single':
            if unit_id not in single_measurements:
                metadata = record['metadata']
                measurement = MeaRaman(timestamp=record['timestamp'],
                    int_time_ms=metadata['integration_time_ms'],
                    laserPower_mW=metadata['laser_power_milliwatt'],
                    laserWavelength_nm=metadata['laser_wavelength_nm'])
                single_measurements[unit_id] = (record, measurement)
            measurement = single_measurements[unit_id][1]
            for frame in record['raw']:
                measurement.set_raw_list(frame)
            continue
        if unit_id not in units:
            unit = MeaRMap_Unit(record['unit_name'], unit_id=unit_id)
            unit.set_dict_metadata(record['unit_metadata'])
            units[unit_id] = unit
            hub.append_mapping_unit(unit)
        measurement = MeaRaman(reconstruct=True)
        measurement.reconstruct(record['timestamp'], record['metadata'], record['averaged'], record['raw'])
        units[unit_id].append_ramanmeasurement_data(record['timestamp'], record['coordinate'], measurement)
    for unit_id, (record, measurement) in single_measurements.items():
        measurement.check_uptodate()
        unit = MeaRMap_Unit(record['unit_name'], unit_id=unit_id)
        unit.append_ramanmeasurement_data(record['timestamp'], record['coordinate'], measurement)
        hub.append_mapping_unit(unit)
    return hub
