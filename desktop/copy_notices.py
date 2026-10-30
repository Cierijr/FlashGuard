"""Preserve distribution licenses and the exact bundled FFmpeg build configuration."""
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import imageio_ffmpeg
out=Path('dist/FlashGuard/licenses');out.mkdir(parents=True,exist_ok=True)
for package in ('numpy','imageio-ffmpeg','pyinstaller'):
    distribution=importlib.metadata.distribution(package)
    for relative in distribution.files or []:
        if any(word in str(relative).lower() for word in ('license','copying','notice')):
            source=Path(distribution.locate_file(relative))
            if source.is_file():
                destination=out/package/str(relative).replace('..','_')
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,destination)
for flag,label in (('-L','LICENSE'),('-version','BUILD')):
    result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),flag],capture_output=True,check=True)
    (out/f'FFmpeg-{label}.txt').write_bytes(result.stdout+result.stderr)

import sys
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():
    shutil.copy2(python_license,out/'Python-LICENSE.txt')
