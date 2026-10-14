"""Serialized command decisions, single operator ownership, and input expiry."""
import secrets
import threading
import time
import config


class CommandError(ValueError):
    """An invalid operator request, rather than a hardware failure."""


class Controller:
    def __init__(self, hardware, clock=time.monotonic):
        self.hardware = hardware
        self.clock = clock
        self.lock = threading.RLock()
        self.session = None
        self.last_input = 0
        self.sequence = -1
        self.motion = "stop"
        self.latch = "unknown"
        self.primed = False
        hardware.drive("stop")

    def _stop(self):
        self.hardware.drive("stop")
        self.motion = "stop"

    def _expire(self):
        if self.session and self.clock() - self.last_input >= config.INPUT_TIMEOUT:
            self._stop()
            # Late packets cannot restart motion after a timeout.
            self.session = None

    def tick(self):
        with self.lock:
            self._expire()

    def acquire(self):
        with self.lock:
            self._expire()
            if self.session:
                raise CommandError("Another control session is active")
            self._stop()
            self.session = secrets.token_urlsafe(24)
            self.last_input = self.clock()
            self.sequence = -1
            return self.session

    def command(self, session, sequence, action):
        with self.lock:
            self._expire()
            if not self.session or session != self.session:
                raise CommandError("Control session expired; release and press again")
            if type(sequence) is not int or sequence <= self.sequence:
                raise CommandError("Old or duplicate command")
            if action not in {"forward", "backward", "left", "right", "stop", "release", "reset"}:
                raise CommandError("Unknown command")
            self.sequence = sequence
            if action in {"release", "reset"}:
                if self.motion != "stop":
                    raise CommandError("Stop before operating the latch")
                if action == "release":
                    if not self.primed:
                        raise CommandError("Reset the latch before releasing")
                    self.hardware.set_latch("open")
                    self.latch = "open"
                    self.primed = False
                else:
                    self.hardware.set_latch("hold")
                    self.latch = "hold"
                    self.primed = True
                self.session = None
            elif action == "stop":
                self._stop()
                self.session = None
            else:
                if self.motion != action:
                    self.hardware.drive(action)
                    self.motion = action
                self.last_input = self.clock()
            return self.status()

    def emergency_stop(self):
        with self.lock:
            self._stop()
            self.session = None

    def status(self):
        with self.lock:
            self._expire()
            return {"motion": self.motion, "latch": self.latch, "primed": self.primed}
