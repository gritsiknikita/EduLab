import tkinter as tk
from pynput import keyboard

def main():
    root = tk.Tk()
    root.title("EduLab LOCK")
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.configure(bg="black")

    label = tk.Label(
        root,
        text="EDULAB EXAM MODE\n\nДоступ заблокирован преподавателем\n\n",
        fg="white",
        bg="black",
        font=("Arial", 28),
        justify="center"
    )
    label.pack(expand=True)

    root.protocol("WM_DELETE_WINDOW", lambda: None)

    state = {"ctrl": False, "shift": False}

    def on_press(key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            state["ctrl"] = True
        if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            state["shift"] = True

     
        if state["ctrl"] and state["shift"]:
            if hasattr(key, "char") and key.char and key.char.lower() == "q":
                root.after(0, root.destroy)
                return False  

    def on_release(key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            state["ctrl"] = False
        if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            state["shift"] = False

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    root.mainloop()

if __name__ == "__main__":
    main()
