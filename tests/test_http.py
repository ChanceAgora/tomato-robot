"""Test HTTP parsing and responses without requiring a listening socket."""
import io
import json
import unittest
from unittest.mock import patch
from controller import Controller
from hardware import SimulatedHardware
from main import make_handler


class Connection:
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = io.BytesIO()

    def settimeout(self, timeout):
        pass

    def makefile(self, mode, *args):
        return self.input

    def sendall(self, data):
        self.output.write(data)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.robot = Controller(SimulatedHardware())
        self.handler = make_handler(self.robot, '<html>Simulation</html>', 'test-token', True)

    def request(self, path, body=None, token=True, host='localhost', raw=None):
        data = b'' if body is None else json.dumps(body).encode()
        if raw is not None:
            data = raw
        method = 'GET' if body is None and raw is None else 'POST'
        headers = f'{method} {path} HTTP/1.0\r\nHost: {host}\r\nContent-Length: {len(data)}\r\n'
        if token:
            headers += 'X-Control-Token: test-token\r\n'
        connection = Connection(headers.encode() + b'\r\n' + data)
        self.handler(connection, ('127.0.0.1', 1234), None)
        head, payload = connection.output.getvalue().split(b'\r\n\r\n', 1)
        code = int(head.split(b' ')[1])
        return code, json.loads(payload) if path != '/' else payload.decode()

    def test_page_and_status(self):
        self.assertEqual(self.request('/')[0], 200)
        code, result = self.request('/status')
        self.assertEqual(code, 200)
        self.assertTrue(result['simulation'])
        self.assertEqual(result['motion'], 'stop')

    def test_command_and_stop_routes(self):
        code, result = self.request('/acquire', {})
        self.assertEqual(code, 200)
        code, result = self.request('/command', {'session': result['session'], 'sequence': 0, 'action': 'forward'})
        self.assertEqual(code, 200)
        self.assertEqual(result['motion'], 'forward')
        self.assertEqual(self.request('/stop', {})[1]['motion'], 'stop')

    @patch("config.ALLOWED_HOSTS", {"localhost", "127.0.0.1"})
    def test_token_host_and_input_validation(self):
        self.assertEqual(self.request('/acquire', {}, token=False)[0], 403)
        self.assertEqual(self.request('/status', host='untrusted.example')[0], 403)
        self.assertEqual(self.request('/command', [])[0], 400)
        self.assertEqual(self.request('/command', raw=b'not json')[0], 400)
        self.assertEqual(self.request('/command', raw=b'x' * 2049)[0], 400)
        self.assertEqual(self.request('/missing')[0], 404)

    def test_hardware_fault_stops_and_calls_shutdown(self):
        faults = []
        self.handler = make_handler(self.robot, '', 'test-token', True,
                                    lambda: faults.append(True))
        session = self.robot.acquire()
        def broken_drive(direction):
            if direction != 'stop':
                raise ValueError('GPIO fault')
        self.robot.hardware.drive = broken_drive
        with self.assertRaises(ValueError):
            self.request('/command', {'session': session, 'sequence': 0, 'action': 'forward'})
        self.assertEqual(faults, [True])
        self.assertIsNone(self.robot.session)

    def test_non_string_actions_are_bad_requests_not_hardware_faults(self):
        faults = []
        self.handler = make_handler(self.robot, '', 'test-token', True,
                                    lambda: faults.append(True))
        session = self.robot.acquire()
        for action in ([], {}, None, 1):
            with self.subTest(action=action):
                self.assertEqual(self.request('/command', {
                    'session': session, 'sequence': 0, 'action': action})[0], 400)
        self.assertEqual(faults, [])
        self.assertEqual(self.request('/command', {
            'session': session, 'sequence': 0, 'action': 'forward'})[0], 200)

    def test_response_disconnect_does_not_shutdown_service(self):
        faults = []
        self.handler = make_handler(self.robot, '', 'test-token', True,
                                    lambda: faults.append(True))
        with patch.object(Connection, 'sendall', side_effect=BrokenPipeError):
            with self.assertRaises(BrokenPipeError):
                self.request('/acquire', {})
        self.assertEqual(faults, [])
        self.assertIsNotNone(self.robot.session)

    def test_body_timeout_does_not_shutdown_service(self):
        faults = []
        self.handler = make_handler(self.robot, '', 'test-token', True,
                                    lambda: faults.append(True))
        class StalledInput(io.BytesIO):
            def read(self, *args):
                raise TimeoutError('Client stopped sending')
        connection = Connection(b'')
        connection.input = StalledInput(
            b'POST /acquire HTTP/1.0\r\nHost: localhost\r\n'
            b'X-Control-Token: test-token\r\nContent-Length: 2\r\n\r\n')
        self.handler(connection, ('127.0.0.1', 1234), None)
        self.assertEqual(faults, [])
        self.assertIsNone(self.robot.session)
