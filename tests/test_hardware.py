"""Verify electrical command mapping using fake GPIO devices."""
import sys
import types
import unittest
from unittest.mock import patch
import config
from hardware import PiHardware


class Device:
    def __init__(self, pin, initial_value=0, **kwargs):
        self.pin = pin
        self.value = initial_value
        self.closed = False

    def off(self):
        self.value = 0

    def close(self):
        self.closed = True


class HardwareTests(unittest.TestCase):
    def test_gpio_requires_explicit_confirmation(self):
        with patch.object(config, 'HARDWARE_CONFIRMED', False):
            with self.assertRaises(ValueError):
                PiHardware()

    def test_pwm_direction_servo_and_cleanup(self):
        gpio = types.SimpleNamespace(DigitalOutputDevice=Device, PWMOutputDevice=Device, Servo=Device)
        with patch.dict(sys.modules, {'gpiozero': gpio}), patch.object(config, 'HARDWARE_CONFIRMED', True):
            hardware = PiHardware()
            self.assertIsNone(hardware.servo.value)
            for command, left, right in [('forward', 1, 1), ('backward', 0, 0), ('left', 0, 1), ('right', 1, 0)]:
                hardware.drive(command)
                self.assertEqual(hardware.left_dir.value, left)
                self.assertEqual(hardware.right_dir.value, right)
                self.assertEqual(hardware.left_pwm.value, config.DRIVE_SPEED)
                self.assertEqual(hardware.right_pwm.value, config.DRIVE_SPEED)
            with patch.object(config, 'LEFT_REVERSED', True):
                hardware.drive('forward')
                self.assertEqual(hardware.left_dir.value, 0)
            hardware.drive('stop')
            self.assertEqual(hardware.left_pwm.value, 0)
            self.assertEqual(hardware.right_pwm.value, 0)
            hardware.set_latch('open')
            self.assertEqual(hardware.servo.value, config.SERVO_OPEN)
            hardware.set_latch('hold')
            self.assertEqual(hardware.servo.value, config.SERVO_HOLD)
            hardware.close()
            self.assertTrue(all(device.closed for device in hardware.outputs))
