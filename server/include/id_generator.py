import time
import threading


class IDGenerator:
    def __init__(self):
        self.last_timestamp = 0
        self.counter = 0
        self.lock = threading.Lock()

    def generate_id(self):
        with self.lock:
            current_timestamp = int(time.time())

            if current_timestamp == self.last_timestamp:
                self.counter += 1
            else:
                self.last_timestamp = current_timestamp
                self.counter = 0

            return f"{current_timestamp}{self.counter:04d}"
