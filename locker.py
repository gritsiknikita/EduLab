import subprocess
import sys
import os

_lock_proc = None

def lock_screen():
    global _lock_proc
    if _lock_proc and _lock_proc.poll() is None:
        return

    path = os.path.join(os.path.dirname(__file__), "locker_window.py")
    _lock_proc = subprocess.Popen([sys.executable, path])

def unlock_screen():
    global _lock_proc
    if _lock_proc and _lock_proc.poll() is None:
        _lock_proc.terminate()
    _lock_proc = None
