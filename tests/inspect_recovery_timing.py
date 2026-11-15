"""Inspect committed acquisition timestamps without loading spectral arrays.

Use only after the scan has stopped. Intervals include exposures, moves,
bleaching and pauses; this tool cannot attribute a delay to autosave alone.
"""
import argparse
from collections import defaultdict
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import statistics


def summarize(timestamps, block):
    gaps = [(b-a)/1e6 for a, b in zip(timestamps, timestamps[1:])]
    def stats(values):
        if not values:
            return None
        ordered = sorted(values)
        return dict(median_s=statistics.median(ordered), max_s=ordered[-1],
                    mean_s=statistics.mean(ordered))
    middle = max(0, (len(gaps)-block)//2)
    return dict(records=len(timestamps), interval_count=len(gaps),
                nonpositive_intervals=sum(value <= 0 for value in gaps),
                elapsed_between_first_last_s=(timestamps[-1]-timestamps[0])/1e6 if timestamps else 0,
                first_block=stats(gaps[:block]), middle_block=stats(gaps[middle:middle+block]),
                last_block=stats(gaps[-block:]))


def inspect(path, block=1000):
    path = Path(path).resolve(strict=True)
    groups = defaultdict(list)
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as connection:
        if connection.execute("SELECT value FROM info WHERE key='format'").fetchone() != ('iris-recovery-v1',):
            raise ValueError('Expected an IRIS recovery journal.')
        for unit_id, timestamp in connection.execute('SELECT unit_id,timestamp FROM spectra ORDER BY sequence'):
            groups[unit_id].append(timestamp)
    count = sum(len(values) for values in groups.values())
    return dict(path=str(path), journal_bytes=path.stat().st_size,
                bytes_per_record=path.stat().st_size/count if count else None,
                note='Recorded intervals include all scan work; they do not isolate autosave delays.',
                units={key: summarize(values, block) for key, values in groups.items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--block', type=int, default=1000)
    args = parser.parse_args()
    if args.block < 1:
        parser.error('--block must be positive.')
    print(json.dumps(inspect(args.journal, args.block), indent=2))
