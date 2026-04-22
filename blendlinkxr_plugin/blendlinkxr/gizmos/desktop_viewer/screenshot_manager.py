import os
import numpy as np
from multiprocessing import shared_memory
import subprocess
import sys

from .screenshot import ScreenCapture

WORKER_FILE = "screenshot_worker.py"


class ScreenshotManager:
    def __init__(self):
        sct = ScreenCapture()
        self.width = sct.screen_width
        self.height = sct.screen_height
        sct.close()

        self.shape = (self.height, self.width, 4)  # RGBA
        # self.shape = self.height * self.width * 4
        self.dtype = np.float32

        self.process = None

        # Create shared memory
        buffer_size = self.height * self.width * 4 * np.dtype(np.float32).itemsize
        self.shared_mem = shared_memory.SharedMemory(create=True, size=buffer_size)

        # Create array interface
        self.arr = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shared_mem.buf)

    def start_capture(self):
        worker_script = os.path.join(os.path.dirname(__file__), WORKER_FILE)
        self.process = subprocess.Popen(
            [
                sys.executable,  # Current Python interpreter
                worker_script,
                self.shared_mem.name,  # Pass shared memory name
                str(self.width),
                str(self.height),
            ]
        )

    def get_frame(self):
        """
        Returns the current frame as a numpy array.
        The array is a view of the shared memory.
        """
        return self.arr.copy()  # Return a copy to prevent modifications

    def cleanup(self):
        """
        Clean up resources
        """
        if self.process is not None:
            self.process.terminate()
            self.process.wait()

            self.process = None
