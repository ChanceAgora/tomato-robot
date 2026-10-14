"""Edit hardware settings here after checking wiring and servo specifications.

GPIO numbers use BCM numbering, not physical header pin numbers.
"""
HOST = "127.0.0.1"
PORT = 8000

# Empty set allows any host to connect
ALLOWED_HOSTS = set()
# {"localhost", "127.0.0.1"}

INPUT_TIMEOUT = 0.4
WATCHDOG_INTERVAL = 0.02
DRIVE_SPEED = 0.35
LEFT_PWM_PIN = 12
LEFT_DIR_PIN = 5
RIGHT_PWM_PIN = 13
RIGHT_DIR_PIN = 6
LEFT_REVERSED = False
RIGHT_REVERSED = False
SERVO_PIN = 18
# Example pulse widths only: check the servo's specification before enabling it.
SERVO_MIN_PULSE = 0.001
SERVO_MAX_PULSE = 0.002
SERVO_HOLD = -0.5
SERVO_OPEN = 0.5
HARDWARE_CONFIRMED = False
