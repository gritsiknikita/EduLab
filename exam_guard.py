import time
import psutil

PROTECTED = {
    "system", "system idle process",
    "wininit.exe", "csrss.exe", "lsass.exe", "services.exe", "svchost.exe",
    "winlogon.exe", "dwm.exe", "explorer.exe",
    "smss.exe", "fontdrvhost.exe", "runtimebroker.exe",
}

class ExamGuard:
    def __init__(self):
        self.enabled = False
        self.mode = "denylist"  
        self.deny = set()
        self.allow = set()

    def set_rules(self, mode: str, deny: list[str] | None = None, allow: list[str] | None = None):
        mode = (mode or "").lower().strip()
        if mode not in ("denylist", "allowlist"):
            mode = "denylist"
        self.mode = mode
        self.deny = {x.lower() for x in (deny or [])}
        self.allow = {x.lower() for x in (allow or [])}

    def on(self):
        self.enabled = True

    def off(self):
        self.enabled = False

    def tick(self):
        """Один проход: закрыть запрещённые процессы."""
        if not self.enabled:
            return

        for p in psutil.process_iter(["pid", "name"]):
            try:
                name = (p.info.get("name") or "").lower()
                if not name:
                    continue
                if name in PROTECTED:
                    continue
                if name in ("python.exe", "pythonw.exe"):
                    continue

                kill = False
                if self.mode == "denylist":
                    if name in self.deny:
                        kill = True
                else:  

                    if name not in self.allow:
                        kill = True

                if kill:
                    p.kill()

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

def run_guard_loop(guard: ExamGuard, stop_flag):
    while not stop_flag["stop"]:
        try:
            guard.tick()
        except Exception:
            pass
        time.sleep(0.7)  
