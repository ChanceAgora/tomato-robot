"""Check the launcher without accessing GPIO or opening a network port."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import types
from hardware import PiHardware
import config
from test_hardware import Device


class LauncherTests(unittest.TestCase):
    def test_script_selects_hardware_from_its_own_directory(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='tomato launcher ') as folder:
            fake_python = Path(folder) / 'python3'
            fake_python.write_text('#!/bin/sh\npwd\nprintf "%s\\n" "$@"\n')
            fake_python.chmod(0o755)
            result = subprocess.run(['sh', str(project / 'start-robot.sh')],
                                    cwd=folder, env={'PATH': folder + ':/usr/bin:/bin'},
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.splitlines(), [str(project), 'main.py', '--hardware'])

    def test_backend_default_and_explicit_override(self):
        gpio = types.SimpleNamespace(DigitalOutputDevice=Device, PWMOutputDevice=Device, Servo=Device)
        for starting, expected in [({}, 'lgpio'), ({'GPIOZERO_PIN_FACTORY': 'pigpio'}, 'pigpio')]:
            with patch('hardware.os.environ', starting), patch.dict('sys.modules', {'gpiozero': gpio}), patch.object(config, 'HARDWARE_CONFIRMED', True):
                hardware = PiHardware()
                self.assertEqual(starting['GPIOZERO_PIN_FACTORY'], expected)
                hardware.close()
