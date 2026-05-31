import ctypes
import time

from ctypes import wintypes

# Input Types
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# Keyboard flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Mouse flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000

# DirectInput Scan Codes
# Refer to standard keyboard scan codes (Set 1 / Set 2)
KEY_X = 0x2D       # 'X' key
KEY_ENTER = 0x1C   # 'Enter' key
KEY_ESC = 0x01     # 'ESC' key
KEY_W = 0x11       # 'W' key (Forward)

# C Structs
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ii", INPUT_UNION),
    ]

# Keyboard Actions
def press_key(scan_code):
    """Presses a key using DirectInput scan code."""
    extra = ctypes.c_void_p(0)
    ii_ = INPUT_UNION()
    ii_.ki = KEYBDINPUT(0, scan_code, KEYEVENTF_SCANCODE, 0, extra)
    x = INPUT(INPUT_KEYBOARD, ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def release_key(scan_code):
    """Releases a key using DirectInput scan code."""
    extra = ctypes.c_void_p(0)
    ii_ = INPUT_UNION()
    ii_.ki = KEYBDINPUT(0, scan_code, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, extra)
    x = INPUT(INPUT_KEYBOARD, ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def press_and_release(scan_code, duration=0.5):
    """Simulates a key press down, waits for duration, releases it, and adds a 0.5s delay."""
    press_key(scan_code)
    time.sleep(duration)
    release_key(scan_code)
    time.sleep(0.5)  # 0.5s delay between keys

# Mouse Actions
def set_cursor_pos(x, y):
    """Moves the cursor to absolute screen coordinates (x, y)."""
    ctypes.windll.user32.SetCursorPos(x, y)

def mouse_click(x, y, click_duration=0.1, settle_delay=0.1):
    """Moves the mouse to (x, y) and performs a left-click."""
    # Move mouse cursor
    set_cursor_pos(x, y)
    time.sleep(settle_delay)
    
    # Left click down
    extra = ctypes.c_void_p(0)
    ii_ = INPUT_UNION()
    ii_.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, extra)
    input_down = INPUT(INPUT_MOUSE, ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(input_down), ctypes.sizeof(input_down))
    
    time.sleep(click_duration)
    
    # Left click up
    ii_up = INPUT_UNION()
    ii_up.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, extra)
    input_up = INPUT(INPUT_MOUSE, ii_up)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(input_up), ctypes.sizeof(input_up))

# Simple test script
if __name__ == "__main__":
    print("DirectInput Test: Waiting 3 seconds, then typing 'X'...")
    time.sleep(3)
    print("Pressing X...")
    press_and_release(KEY_X)
    print("Done.")
