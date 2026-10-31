"""Atomic per-user recovery state. No video files or full video frames are copied."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys


def data_directory():
    if os.environ.get('FLASHGUARD_DATA_DIR'):
        return Path(os.environ['FLASHGUARD_DATA_DIR'])
    base = Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local'/'share'))
    return base/'FlashGuard'


def fingerprint(path):
    path=Path(path).resolve()
    stat=path.stat()
    digest=hashlib.sha256()
    with path.open('rb') as source:
        digest.update(source.read(65536))
        source.seek(max(0,stat.st_size-65536))
        digest.update(source.read(65536))
    return dict(path=str(path),size=stat.st_size,modified=stat.st_mtime_ns,edges=digest.hexdigest())


class SessionStore:
    def __init__(self,directory=None):
        self.directory=Path(directory) if directory else data_directory()
        self.directory.mkdir(parents=True,exist_ok=True)
        if os.name!='nt':
            self.directory.chmod(0o700)
        self.path=self.directory/'analysis-session.json.gz'
        self.runtime=self.directory/'running.json'
        self.lockfile=None
        self.warning=None

    def save(self,data):
        temporary=self.path.with_suffix('.tmp')
        with gzip.open(temporary,'wt',encoding='utf-8') as stream:
            json.dump(data,stream,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        if os.name!='nt':
            temporary.chmod(0o600)
        temporary.replace(self.path)

    def load(self):
        try:
            with gzip.open(self.path,'rt',encoding='utf-8') as stream:
                data=json.load(stream)
            if not isinstance(data,dict):
                raise ValueError('Invalid saved session')
            if data.get('schema')!=1 or data.get('status') not in ('partial','complete'):
                raise ValueError('Unsupported saved session')
            if data['status']=='complete' and (not isinstance(data.get('result'),dict) or not data['result'].get('complete')):
                raise ValueError('Invalid completed report')
            if data['status']=='partial' and not all(key in data for key in ('count','events','cues','previous')):
                raise ValueError('Invalid partial checkpoint')
            identity=data['identity']
            if fingerprint(identity['path'])!=identity:
                raise ValueError('The original video changed after progress was saved.')
            return data
        except FileNotFoundError:
            if self.path.exists():
                self.warning='The saved video was moved or deleted. Choose the original video again.'
            return None
        except (OSError,ValueError,KeyError,TypeError,EOFError):
            self.warning='Saved progress could not be restored. The video may have changed. Choose a video to start a new analysis.'
            return None

    def clear(self):
        self.path.unlink(missing_ok=True)

    def acquire(self):
        self.lockfile=(self.directory/'instance.lock').open('a+b')
        # Windows denies reading a byte another instance has locked.
        # Inspect file size without reading the locked range.
        if os.fstat(self.lockfile.fileno()).st_size==0:
            self.lockfile.write(b'0');self.lockfile.flush()
        self.lockfile.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.lockfile.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.lockfile.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            return True
        except OSError:
            self.lockfile.close();self.lockfile=None
            return False

    def release(self):
        if self.lockfile:
            self.lockfile.close();self.lockfile=None
