# Tomato Robot

A small Python controller for a Raspberry Pi 3 B+, two brushed DC wheel motors
through a Cytron MDD10A Rev2.0, and a positional servo operating a carriage latch.
Use a phone browser connected through Tailscale. Elastic-band tensioning and
carriage loading are manual.

## Start in simulation

Copy this whole folder to the Pi. Python 3 is sufficient for simulation; no
third-party packages are needed. From this folder:

```sh
python3 main.py
```

On the same computer, open http://127.0.0.1:8000. The page says **SIMULATION**.
The motors and servo are represented in memory; no GPIO pins are accessed.

### Phone access through Tailscale

1. Connect the phone and Pi to the same Tailscale network.
2. In `config.py`, add the Pi's exact Tailscale Serve hostname to `ALLOWED_HOSTS`,
   for example `tomato-pi.example-tailnet.ts.net`. Keep the existing local names.
3. Restart the Python program if you edited configuration.
4. In another terminal on the Pi, run:

   ```sh
   tailscale serve --bg http://127.0.0.1:8000
   ```

5. Open the HTTPS address printed by Tailscale on your phone. Tailscale may ask
   you to enable HTTPS for the tailnet. Tailnet access rules must permit the phone
   to reach the Pi. Use Serve for private access; do not expose this controller
   through a public service.

The server listens only on loopback by default. Tailscale Serve forwards requests
there. SSH is useful for starting/stopping the program; movement uses the web page.
Stop Python with Ctrl+C. `tailscale serve reset` removes the Serve configuration
for this Pi, including other Serve routes if any exist.

## Controls and behavior

- Hold a direction button to drive; release it to stop. One direction at a time.
- Forward/backward run both motors together. Left/right turn them in opposite
  directions. The chassis needs freely moving support wheels for these turns.
- The browser sends one movement request at a time, about every 100 ms plus
  request duration. No fresh movement command for 400 ms expires the session and
  stops the motors. The Pi checks every 20 ms using a monotonic clock.
- Tab hiding, loss of focus, cancelled touch, and detected connection failure
  end movement. Stop messages are best effort; the Pi timeout is independent.
- Old/duplicate sequence numbers are rejected. Expired session packets cannot
  restart motion. Release and press again to create a new session.
- Only one session owns control at a time. Stop is available to every authorized
  page. A slow connection can cause stops; it does not justify indefinite motion.
- Startup stops both motors and sends no servo position command. Release is
  disabled until **Reset latch** is pressed.
- **Reset latch** commands the holding position and primes one release. It does
  not tension the carriage and does not verify engagement: there is no latch sensor.
- **Release** requires stopped motors and a primed latch, commands the open
  position, and consumes the prime. The servo stays commanded open until Reset.
- Disconnecting preserves latch state. Restarting clears software priming and
  requires Reset again. Shutdown stops motors and disables GPIO outputs; the
  servo's physical position under load is not guaranteed after power or pulses end.

## Hardware setup — before enabling GPIO

The settings are deliberately examples. Set `HARDWARE_CONFIRMED = True` only after
checking the following with your actual parts. Hardware mode is selected explicitly:

```sh
python3 main.py --hardware
```

Install GPIO Zero and a supported GPIO backend on the Pi. With Debian 13, a
system-package setup to try is:

```sh
sudo apt update
sudo apt install python3-gpiozero python3-lgpio
GPIOZERO_PIN_FACTORY=lgpio python3 main.py --hardware
```

Package availability, GPIO device permissions, and kernel support depend on the
Pi's OS image. If these packages or GPIO devices are unavailable, resolve that
before hardware mode; simulation remains usable. `requirements.txt` declares the
Python library, but a GPIO backend is also required. Do not install packages into
Debian's system Python with pip. GPIO Zero supports alternative backends; servo
jitter may require a different timing backend or a dedicated servo controller.

### Example signal wiring

Numbers in configuration use **BCM GPIO numbers**. Physical header pin numbers
below are included to avoid mixing the two systems. Verify the board labels.

| Pi signal | Physical header pin | Destination |
|---|---:|---|
| GPIO12 | 32 | MDD10A PWM1 |
| GPIO5 | 29 | MDD10A DIR1 |
| GPIO13 | 33 | MDD10A PWM2 |
| GPIO6 | 31 | MDD10A DIR2 |
| GPIO18 | 12 | Servo signal |
| GND | 6 | Driver signal ground and servo supply ground |

Left motor connects to channel 1; right motor to channel 2. Use sign-magnitude
PWM/DIR operation. PWM zero stops the drive command. Both PWM values are removed
before changing direction. `LEFT_REVERSED` and `RIGHT_REVERSED` correct mirrored
motor mounting without changing movement logic. Speed starts at 35% duty cycle.

The MDD10A's power input accepts 5–30 V, but the specified TT motors are 3–6 V:
choose a motor supply within both ratings, accounting for actual battery voltage.
The driver is not a voltage regulator. Never supply motor power through GPIO.
The MDD10A lacks reverse-polarity protection. Confirm polarity before powering it.

Identify the servo first. This code expects a **positional servo**, not a
continuous-rotation servo. Supply it at its specified voltage using a source
capable of its required current, with a common signal ground. Verify its 3.3 V
signal compatibility. Power the Pi through an appropriate regulated supply.
Do not assume the Pi's header can supply the motor or servo load.

Calibrate `SERVO_MIN_PULSE`, `SERVO_MAX_PULSE`, `SERVO_HOLD`, and `SERVO_OPEN`
with the bands unloaded. Position values are between -1 and 1 within the pulse
range. Avoid mechanically forcing the servo against its travel limits. Check that
it can operate the latch under the intended load. A mechanical latch should carry
the elastic-band load rather than relying on continuous servo torque alone.

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q main.py controller.py hardware.py config.py tests
```

Automated tests cover direction commands, timeout and renewal, stale packets,
operator ownership, input validation, startup, release/reset, and stop behavior.
The default HTTP tests exercise request parsing without opening a network port.
For a live server and independent watchdog check on your Pi, stop any existing
server and run:

```sh
python3 -m unittest discover -s tests -p live_http_check.py -v
```

The live check needs permission to listen on the default local port. Browser touch
behavior and real GPIO still require the manual checks below.

Before a loaded demonstration:

1. In simulation, try each button and reset/release; verify a second release
   requires reset. Switch apps while holding a direction and observe stopped state.
2. Lift the wheels, enable hardware, and verify direction and turning.
3. Hold a direction and disconnect the phone's network/Tailscale. Measure actual
   stopping time; repeat with screen lock and tab switching.
4. Test the latch unloaded, then test the complete mechanism in a clear area.
5. Keep a physical power cutoff accessible.

The timeout is an application-level stop while Python and the Pi are operating.
It cannot guarantee shutdown during a frozen process, OS crash, or stuck GPIO
output. A hardware watchdog/interlock is needed for that guarantee. Stop removes
motor drive; actual stopping distance depends on speed, inertia, and driver braking.

## Files

- `config.py`: pin assignments, timing, speed, and calibration.
- `hardware.py`: simulated outputs and real MDD10A/servo outputs.
- `controller.py`: session ownership, movement expiry, latch state.
- `main.py`: local HTTP server and independent watchdog thread.
- `static/index.html`: touch interface and movement heartbeat.
- `tests/`: standard-library automated tests.

Hardware documentation: [Cytron MDD10A](https://www.cytron.io/c-dc-motor-drivers/p-10amp-5v-30v-dc-motor-driver-2-channels),
[GPIO Zero](https://gpiozero.readthedocs.io/en/stable/),
[Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve).
