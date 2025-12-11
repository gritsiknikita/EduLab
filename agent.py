import asyncio, json, socket, webbrowser
import websockets
from locker import lock_screen, unlock_screen
import threading
from exam_guard import ExamGuard, run_guard_loop
import psutil
import win32gui
import win32process

SYSTEM_EXES = {
    "system", "system idle process",
    "svchost.exe", "services.exe", "wininit.exe", "winlogon.exe",
    "csrss.exe", "smss.exe", "dwm.exe", "explorer.exe",
    "lsass.exe", "conhost.exe", "fontdrvhost.exe",
    "runtimebroker.exe", "searchhost.exe", "sihost.exe",
}

def list_running_apps():
    """Возвращает список видимых оконных программ (тех, что на панели задач)"""
    apps = set()

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                p = psutil.Process(pid)
                name = p.name()
                if name.lower() not in ("explorer.exe", "searchui.exe", "taskmgr.exe"):
                    apps.add(name)
            except Exception:
                pass
        return True

    win32gui.EnumWindows(callback, None)
    return sorted(apps)


exam = ExamGuard()
stop_flag = {"stop": False}
guard_thread = threading.Thread(target=run_guard_loop, args=(exam, stop_flag), daemon=True)
guard_thread.start()


SERVER = "ws://localhost:8010/ws/agent"
PC_ID = socket.gethostname()

locked_state = False

async def handle_command(msg):
    global locked_state
    ctype = msg.get("type")
    payload = msg.get("payload", {})

    if ctype == "LOCK":
        locked_state = True
        lock_screen()
        print("LOCKED")
    elif ctype == "UNLOCK":
        locked_state = False
        unlock_screen()
        print("UNLOCKED")
    elif ctype == "OPEN_URL":
        url = payload.get("url")
        if url:
            webbrowser.open(url)
            print("OPEN_URL", url)
    elif ctype == "EXAM_SET":
        mode = payload.get("mode", "denylist")
        deny = payload.get("deny", [])
        allow = payload.get("allow", [])
        exam.set_rules(mode=mode, deny=deny, allow=allow)
        print("EXAM_SET", mode, "deny=", len(deny), "allow=", len(allow))

    elif ctype == "EXAM_ON":
        exam.on()
        print("EXAM_ON")

    elif ctype == "EXAM_OFF":
        exam.off()
        print("EXAM_OFF")

async def main():
    async with websockets.connect(SERVER) as ws:
        print("Connected to", SERVER)
        await ws.send(json.dumps({"type":"HELLO","pc_id":PC_ID,"name":PC_ID,"room":"101"}))

        async def heartbeat():
            while True:
                await ws.send(json.dumps({"type":"HEARTBEAT","pc_id":PC_ID,"locked":locked_state, "apps": list_running_apps()}))
                await asyncio.sleep(2)

        asyncio.create_task(heartbeat())

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            while True:
                msg = await ws.recv()
                data = json.loads(msg)

                ctype = data.get("type")
                if not ctype:
                    continue

                cmd_id = data.get("id")
                try:
                    await handle_command(data)
                    await ws.send(json.dumps({"type":"RESULT","id":cmd_id,"ok": True}))
                except Exception as e:
                    await ws.send(json.dumps({"type":"RESULT","id":cmd_id,"ok": False, "error": str(e)}))
asyncio.run(main())
