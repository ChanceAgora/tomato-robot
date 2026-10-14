import unittest
import config
from controller import Controller
from hardware import SimulatedHardware


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.hardware = SimulatedHardware()
        self.robot = Controller(self.hardware, clock=lambda: self.now)

    def send(self, action):
        session = self.robot.acquire()
        return self.robot.command(session, 0, action)

    def test_startup_does_not_move_servo_or_prime(self):
        self.assertEqual(self.hardware.motion, 'stop')
        self.assertEqual(self.hardware.latch, 'unknown')
        self.assertFalse(self.robot.primed)
        with self.assertRaises(ValueError):
            self.send('release')

    def test_all_directions_and_explicit_stop(self):
        for direction in ('forward', 'backward', 'left', 'right'):
            session = self.robot.acquire()
            self.robot.command(session, 0, direction)
            self.assertEqual(self.hardware.motion, direction)
            self.robot.command(session, 1, 'stop')
            self.assertEqual(self.hardware.motion, 'stop')

    def test_heartbeat_renews_then_timeout_invalidates_session(self):
        session = self.robot.acquire()
        self.robot.command(session, 0, 'forward')
        self.now += config.INPUT_TIMEOUT / 2
        self.robot.command(session, 1, 'forward')
        self.now += config.INPUT_TIMEOUT / 2
        self.robot.tick()
        self.assertEqual(self.hardware.motion, 'forward')
        self.now += config.INPUT_TIMEOUT
        self.robot.tick()
        self.assertEqual(self.hardware.motion, 'stop')
        with self.assertRaises(ValueError):
            self.robot.command(session, 2, 'forward')
        self.assertEqual(self.hardware.motion, 'stop')

    def test_late_packet_expires_even_before_watchdog_tick(self):
        session = self.robot.acquire()
        self.robot.command(session, 0, 'forward')
        self.now += 1
        with self.assertRaises(ValueError):
            self.robot.command(session, 1, 'forward')
        self.assertEqual(self.hardware.motion, 'stop')

    def test_duplicate_and_out_of_order_commands_rejected(self):
        session = self.robot.acquire()
        self.robot.command(session, 2, 'left')
        for sequence in (2, 1, True, '3'):
            with self.assertRaises(ValueError):
                self.robot.command(session, sequence, 'right')
        self.assertEqual(self.hardware.motion, 'left')

    def test_only_one_operator_and_invalid_command(self):
        session = self.robot.acquire()
        with self.assertRaises(ValueError):
            self.robot.acquire()
        with self.assertRaises(ValueError):
            self.robot.command('wrong', 0, 'forward')
        with self.assertRaises(ValueError):
            self.robot.command(session, 0, 'diagonal')
        self.assertEqual(self.hardware.motion, 'stop')

    def test_release_stays_open_until_reset_and_does_not_repeat(self):
        self.send('reset')
        session = self.robot.acquire()
        self.robot.command(session, 0, 'release')
        self.assertEqual(self.hardware.latch, 'open')
        self.assertFalse(self.robot.primed)
        with self.assertRaises(ValueError):
            self.robot.command(session, 1, 'release')
        with self.assertRaises(ValueError):
            self.send('release')
        self.robot.emergency_stop()
        self.send('reset')
        self.assertEqual(self.hardware.latch, 'hold')
        self.assertTrue(self.robot.primed)

    def test_latch_rejected_while_driving(self):
        session = self.robot.acquire()
        self.robot.command(session, 0, 'forward')
        for seq, action in enumerate(('reset', 'release'), 1):
            with self.assertRaises(ValueError):
                self.robot.command(session, seq, action)
        self.assertEqual(self.hardware.latch, 'unknown')

    def test_stop_preserves_latch_and_old_session_cannot_resume(self):
        self.send('reset')
        session = self.robot.acquire()
        self.robot.command(session, 0, 'forward')
        self.robot.emergency_stop()
        self.assertTrue(self.robot.primed)
        self.assertEqual(self.hardware.latch, 'hold')
        with self.assertRaises(ValueError):
            self.robot.command(session, 1, 'forward')
        self.assertEqual(self.robot.acquire() is not None, True)


if __name__ == '__main__':
    unittest.main()
