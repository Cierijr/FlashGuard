"""Select the existing FlashGuard browser tab using Windows accessibility APIs."""
import os
from pathlib import Path
import subprocess


def focus_existing(marker):
    if os.name != 'nt':
        return False
    script = Path(__file__).with_name('focus_browser.ps1').read_text(encoding='utf-8')
    try:
        result = subprocess.run(['powershell.exe','-Mta','-NoProfile','-NonInteractive','-Command',
            '& {\n'+script+'\n} -Marker '+marker],capture_output=True,timeout=6,
            creationflags=subprocess.CREATE_NO_WINDOW)
        return result.returncode == 0
    except (OSError,subprocess.TimeoutExpired):
        return False
