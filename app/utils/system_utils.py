"""
Operating system integration utilities (Windows file launch, explorer selection, clipboard).
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


def open_file(file_path: str) -> bool:
    """Opens a file with the system default associated player/program."""
    try:
        p = Path(file_path).resolve()
        if not p.exists():
            return False
        if os.name == "nt":
            os.startfile(str(p))
            return True
        else:
            subprocess.run(["xdg-open", str(p)], check=False)
            return True
    except Exception:
        return False


def open_folder(folder_path: str) -> bool:
    """Opens a directory in Windows Explorer."""
    try:
        p = Path(folder_path).resolve()
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(p))
            return True
        else:
            subprocess.run(["xdg-open", str(p)], check=False)
            return True
    except Exception:
        return False


def show_in_file_manager(file_path: str) -> bool:
    """Reveals and selects the given file inside Windows Explorer."""
    try:
        p = Path(file_path).resolve()
        if not p.exists():
            return open_folder(str(p.parent))
        if os.name == "nt":
            # Using explorer.exe /select,"path"
            subprocess.run(f'explorer /select,"{p}"', shell=True, check=False)
            return True
        else:
            return open_folder(str(p.parent))
    except Exception:
        return False
