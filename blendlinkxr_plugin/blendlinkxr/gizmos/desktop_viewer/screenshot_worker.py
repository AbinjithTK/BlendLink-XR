# This must be a completely standalone script that can be spawned
import sys
import numpy as np
import time
from multiprocessing import shared_memory

from screenshot import ScreenCapture

FPS = 3

if __name__ == "__main__":
    # Get arguments passed from parent process
    shared_memory_name = sys.argv[1]
    width = int(sys.argv[2])
    height = int(sys.argv[3])

    # Attach to existing shared memory
    shape = (height, width, 4)  # RGBA
    # shape = height * width * 4
    shared_mem = shared_memory.SharedMemory(name=shared_memory_name)
    arr = np.ndarray(shape, dtype=np.float32, buffer=shared_mem.buf)

    # Initialize screen capture
    sct = ScreenCapture()

    try:
        while True:
            # Capture screenshot
            frame = sct.grab()

            # Update shared memory
            np.copyto(arr, frame)

            time.sleep(1.0 / FPS)

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        shared_mem.close()
        sct.close()
