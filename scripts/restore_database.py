"""Restore a pre-migration SQLite backup to a NEW path. Stop service before switching."""
import argparse
import os
from pathlib import Path
import sqlite3

def restore(source,destination):
    source,destination=Path(source),Path(destination)
    if not source.is_file():raise ValueError('backup missing')
    # Exclusive creation prevents accidental replacement, including symlink targets.
    descriptor=os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    os.close(descriptor)
    try:
        with sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True) as src:
            if src.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('invalid backup')
            with sqlite3.connect(destination) as dst:
                src.backup(dst)
                if dst.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('restore failed')
    except Exception:
        destination.unlink();raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('backup');p.add_argument('new_database');a=p.parse_args()
    restore(a.backup,a.new_database);print('Restored to a new path. Stop service before configuring it; do not mix WAL files.')
