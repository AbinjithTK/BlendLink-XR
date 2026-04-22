import ctypes
import sys
import numpy as np


class ScreenCapture:
    def __init__(self):
        self.is_windows = sys.platform.startswith("win")

        self.screen_width = 100
        self.screen_height = 100

        if self.is_windows:
            self.user32 = ctypes.windll.user32
            self.gdi32 = ctypes.windll.gdi32
            self.kernel32 = ctypes.windll.kernel32

            self.hdc_screen = self.user32.GetDC(0)
            self.hdc_mem = self.gdi32.CreateCompatibleDC(self.hdc_screen)

            self.screen_width = self.user32.GetSystemMetrics(0)
            self.screen_height = self.user32.GetSystemMetrics(1)

            self.hbitmap = self.gdi32.CreateCompatibleBitmap(self.hdc_screen, self.screen_width, self.screen_height)
            self.gdi32.SelectObject(self.hdc_mem, self.hbitmap)

            self.bmp_info = ctypes.create_string_buffer(40)
            ctypes.memset(self.bmp_info, 0, 40)
            ctypes.cast(self.bmp_info, ctypes.POINTER(ctypes.c_ulong))[0] = 40
            ctypes.cast(self.bmp_info, ctypes.POINTER(ctypes.c_ulong))[1] = self.screen_width
            ctypes.cast(self.bmp_info, ctypes.POINTER(ctypes.c_ulong))[2] = -self.screen_height  # Invert the height
            ctypes.cast(self.bmp_info, ctypes.POINTER(ctypes.c_ushort))[6] = 1
            ctypes.cast(self.bmp_info, ctypes.POINTER(ctypes.c_ushort))[7] = 32

            self.bits = (ctypes.c_byte * (self.screen_width * self.screen_height * 4))()

    def grab(self):
        if not self.is_windows:
            return np.zeros((self.screen_height, self.screen_width, 4), dtype=np.float32)

        self.gdi32.BitBlt(self.hdc_mem, 0, 0, self.screen_width, self.screen_height, self.hdc_screen, 0, 0, 0x00CC0020)
        self.gdi32.GetDIBits(
            self.hdc_mem, self.hbitmap, 0, self.screen_height, ctypes.byref(self.bits), self.bmp_info, 0
        )

        arr = np.frombuffer(self.bits, dtype=np.uint8).reshape((self.screen_height, self.screen_width, 4))
        arr = arr[..., [2, 1, 0, 3]]
        arr = arr.astype(np.float32) / 255

        return arr

    def close(self):
        if not self.is_windows:
            return

        self.gdi32.DeleteObject(self.hbitmap)
        self.gdi32.DeleteDC(self.hdc_mem)
        self.user32.ReleaseDC(0, self.hdc_screen)
