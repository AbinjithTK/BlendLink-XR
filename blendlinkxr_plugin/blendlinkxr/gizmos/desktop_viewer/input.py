import platform
import ctypes


class InputTracker:
    def __init__(self):
        self.os_name = platform.system().lower()

        if self.os_name == "windows":
            self.user32 = ctypes.windll.user32

    def get_mouse_pos(self):
        """
        Returns the current mouse cursor coordinates as a tuple (x, y)
        Returns (0, 0) on non-Windows systems
        """
        if self.os_name != "windows":
            return (0, 0)

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        pt = POINT()
        self.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    def is_key_pressed(self):
        """
        Returns True if any keyboard key is currently pressed, False otherwise
        Returns False on non-Windows systems
        """
        if self.os_name != "windows":
            return False

        # Check all virtual key codes from 0x01 to 0xFE
        for i in range(1, 255):
            if self.user32.GetAsyncKeyState(i) & 0x8000:
                return True
        return False

    def is_mouse_pressed(self):
        """
        Returns True if the left mouse button is currently pressed, False otherwise
        Returns False on non-Windows systems
        """
        if self.os_name != "windows":
            return False

        # Check if the left mouse button is pressed (0x01)
        return self.user32.GetAsyncKeyState(0x01) & 0x8000 != 0
