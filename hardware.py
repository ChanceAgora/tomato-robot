"""Simulated hardware and the Cytron MDD10A PWM/DIR interface."""
import os
import config


class SimulatedHardware:
    def __init__(self):
        self.motion = "stop"
        self.latch = "unknown"

    def drive(self, direction):
        self.motion = direction

    def set_latch(self, position):
        self.latch = position

    def close(self):
        self.drive("stop")


class PiHardware:
    def __init__(self):
        if not config.HARDWARE_CONFIRMED:
            raise ValueError("Check wiring and servo settings; then set HARDWARE_CONFIRMED=True")
        if not 0 <= config.DRIVE_SPEED <= 1:
            raise ValueError("DRIVE_SPEED must be between 0 and 1")
        if not 0 < config.SERVO_MIN_PULSE < config.SERVO_MAX_PULSE < 0.02:
            raise ValueError("Servo pulse widths must increase and fit the 20 ms period")
        if not all(-1 <= value <= 1 for value in (config.SERVO_HOLD, config.SERVO_OPEN)):
            raise ValueError("Servo positions must be between -1 and 1")
        pins = (config.LEFT_PWM_PIN, config.LEFT_DIR_PIN, config.RIGHT_PWM_PIN,
                config.RIGHT_DIR_PIN, config.SERVO_PIN)
        if len(set(pins)) != len(pins):
            raise ValueError("Each output requires a different GPIO pin")
        # Select the Pi backend automatically; allow an explicit environment override.
        os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
        from gpiozero import DigitalOutputDevice, PWMOutputDevice, Servo
        self.outputs = []
        try:
            self.left_pwm = self._track(PWMOutputDevice(config.LEFT_PWM_PIN, initial_value=0))
            self.right_pwm = self._track(PWMOutputDevice(config.RIGHT_PWM_PIN, initial_value=0))
            self.left_dir = self._track(DigitalOutputDevice(config.LEFT_DIR_PIN))
            self.right_dir = self._track(DigitalOutputDevice(config.RIGHT_DIR_PIN))
            # None avoids commanding a latch position at startup.
            self.servo = self._track(Servo(config.SERVO_PIN, initial_value=None,
                                          min_pulse_width=config.SERVO_MIN_PULSE,
                                          max_pulse_width=config.SERVO_MAX_PULSE))
        except Exception:
            self.close()
            raise

    def _track(self, device):
        self.outputs.append(device)
        return device

    def drive(self, direction):
        left, right = {"stop": (0, 0), "forward": (1, 1), "backward": (-1, -1),
                       "left": (-1, 1), "right": (1, -1)}[direction]
        # Remove drive before changing direction; never reverse an energized output.
        self.left_pwm.off()
        self.right_pwm.off()
        self.left_dir.value = int((left > 0) != config.LEFT_REVERSED)
        self.right_dir.value = int((right > 0) != config.RIGHT_REVERSED)
        self.left_pwm.value = abs(left) * config.DRIVE_SPEED
        self.right_pwm.value = abs(right) * config.DRIVE_SPEED

    def set_latch(self, position):
        self.servo.value = config.SERVO_HOLD if position == "hold" else config.SERVO_OPEN

    def close(self):
        for name in ("left_pwm", "right_pwm"):
            device = getattr(self, name, None)
            if device is not None:
                device.off()
        for device in reversed(self.outputs):
            device.close()
