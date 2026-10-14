"""Exercise the real simulation server, including its independent watchdog."""
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.process = subprocess.Popen([sys.executable, 'main.py'], cwd=Path(__file__).resolve().parents[1],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        cls.addClassCleanup(cls.cleanup)
        for _ in range(50):
            if cls.process.poll() is not None:
                raise RuntimeError(cls.process.stderr.read().decode())
            try:
                with urlopen('http://127.0.0.1:8000/', timeout=1) as response:
                    page = response.read().decode()
                cls.token = re.search("const token = '([^']+)'", page).group(1)
                return
            except URLError:
                time.sleep(0.05)
        raise RuntimeError('Server did not start')

    @classmethod
    def cleanup(cls):
        cls.process.terminate()
        cls.process.wait(timeout=5)
        cls.process.stderr.close()

    def request(self, path, body=None, token=True, host=None):
        headers = {}
        if token:
            headers['X-Control-Token'] = self.token
        if host:
            headers['Host'] = host
        data = None if body is None else json.dumps(body).encode()
        with urlopen(Request('http://127.0.0.1:8000' + path, data=data, headers=headers), timeout=2) as response:
            return json.loads(response.read())

    def setUp(self):
        self.request('/stop', {})

    def test_http_watchdog_release_and_reset(self):
        session = self.request('/acquire', {})['session']
        self.request('/command', {'session': session, 'sequence': 0, 'action': 'forward'})
        time.sleep(0.55)
        self.assertEqual(self.request('/status')['motion'], 'stop')
        with self.assertRaises(HTTPError) as error:
            self.request('/command', {'session': session, 'sequence': 1, 'action': 'forward'})
        self.assertEqual(error.exception.code, 400)
        for action in ('reset', 'release'):
            session = self.request('/acquire', {})['session']
            result = self.request('/command', {'session': session, 'sequence': 0, 'action': action})
        self.assertEqual(result['latch'], 'open')
        self.assertFalse(result['primed'])

    def test_mutations_require_page_token_and_host_allowlist(self):
        with self.assertRaises(HTTPError) as error:
            self.request('/acquire', {}, token=False)
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError) as error:
            self.request('/status', host='untrusted.example')
        self.assertEqual(error.exception.code, 403)

    def test_bad_input_does_not_break_service(self):
        with self.assertRaises(HTTPError) as error:
            self.request('/command', [])
        self.assertEqual(error.exception.code, 400)
        self.assertTrue(self.request('/status')['simulation'])
