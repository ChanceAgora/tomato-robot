"""Run the local phone-control server: python3 main.py [--hardware]."""
import argparse
import json
from pathlib import Path
import secrets
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import config
from controller import CommandError, Controller
from hardware import PiHardware, SimulatedHardware


def make_handler(controller, page, page_token, simulation, on_fault=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not put control credentials into request logs.

        def respond(self, code, body, content_type="application/json"):
            payload = body.encode() if isinstance(body, str) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(payload)

        def allowed_host(self):
            host = self.headers.get("Host", "").split(":")[0].lower()
            if config.ALLOWED_HOSTS and host not in config.ALLOWED_HOSTS:
                self.respond(403, {"error": "Add this hostname to config.ALLOWED_HOSTS"})
                return False
            return True

        def do_GET(self):
            if not self.allowed_host():
                return
            if self.path == "/":
                self.respond(200, page, "text/html; charset=utf-8")
            elif self.path == "/status":
                self.respond(200, {**controller.status(), "simulation": simulation})
            else:
                self.respond(404, {"error": "Not found"})

        def do_POST(self):
            if not self.allowed_host():
                return
            if not secrets.compare_digest(self.headers.get("X-Control-Token", "").encode(), page_token.encode()):
                self.respond(403, {"error": "Open the control page first"})
                return
            try:
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError as error:
                    raise CommandError("Invalid request size") from error
                if not 0 < length <= 2048:
                    raise CommandError("Invalid request size")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise CommandError("Expected an object")
                if self.path == "/acquire":
                    result = {"session": controller.acquire()}
                elif self.path == "/command":
                    result = controller.command(data.get("session"), data.get("sequence"), data.get("action"))
                elif self.path == "/stop":
                    controller.emergency_stop()
                    result = controller.status()
                else:
                    self.respond(404, {"error": "Not found"})
                    return
                self.respond(200, result)
            except (CommandError, json.JSONDecodeError, UnicodeDecodeError) as error:
                self.respond(400, {"error": str(error)})
            except Exception:
                # Hardware errors must stop motion and terminate the service.
                try:
                    controller.emergency_stop()
                finally:
                    if on_fault is not None:
                        on_fault()
                raise

        def setup(self):
            super().setup()
            self.connection.settimeout(2)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hardware", action="store_true", help="Enable actual GPIO outputs")
    args = parser.parse_args()
    hardware = PiHardware() if args.hardware else SimulatedHardware()
    controller = Controller(hardware)
    page_token = secrets.token_urlsafe(32)
    page = Path(__file__).with_name("static").joinpath("index.html").read_text().replace("__TOKEN__", page_token)
    done = threading.Event()

    def on_fault():
        done.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    Handler = make_handler(controller, page, page_token, not args.hardware, on_fault)

    def watchdog():
        while not done.wait(config.WATCHDOG_INTERVAL):
            try:
                controller.tick()
            except Exception:
                # A GPIO fault ends the service instead of silently losing the watchdog.
                import traceback
                traceback.print_exc()
                done.set()
                server.shutdown()
                return

    def shutdown(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, shutdown)
    try:
        server = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
        worker = threading.Thread(target=watchdog, daemon=True)
        worker.start()
        print(f"{'HARDWARE' if args.hardware else 'SIMULATION'}: http://{config.HOST}:{config.PORT}")
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        done.set()
        try:
            controller.emergency_stop()
        finally:
            hardware.close()
            if 'server' in locals():
                server.server_close()


if __name__ == "__main__":
    main()
