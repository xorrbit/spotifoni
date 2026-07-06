#!/usr/bin/env python3
"""Spotifoni GPIO control daemon — reads rotary encoder, controls volume and transport."""

import signal
import subprocess
import sys
import threading
import time

try:
    from gpiozero import RotaryEncoder, Button
except ImportError:
    print("gpiozero not available — install with: sudo apt install python3-gpiozero")
    sys.exit(1)

VOLUME_CLK = 17
VOLUME_DT = 27
VOLUME_SW = 22

VOLUME_STEP = 5
DEBOUNCE_SEC = 0.3

last_press = 0


def set_volume(delta):
    direction = f"{delta}%+" if delta > 0 else f"{abs(delta)}%-"
    subprocess.run(["amixer", "sset", "Master", direction],
                   capture_output=True, check=False)


def toggle_play_pause():
    subprocess.run(
        ["dbus-send", "--print-reply", "--dest=org.mpris.MediaPlayer2.raspotify",
         "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player.PlayPause"],
        capture_output=True, check=False)


def on_volume_rotate(encoder):
    if encoder.steps > 0:
        set_volume(VOLUME_STEP)
    else:
        set_volume(-VOLUME_STEP)
    encoder.steps = 0


def on_volume_press():
    global last_press
    now = time.monotonic()
    if now - last_press < DEBOUNCE_SEC:
        return
    last_press = now
    toggle_play_pause()


def main():
    encoder = RotaryEncoder(VOLUME_CLK, VOLUME_DT, max_steps=0, wrap=False)
    button = Button(VOLUME_SW, pull_up=True, bounce_time=0.05)

    encoder.when_rotated = lambda: on_volume_rotate(encoder)
    button.when_pressed = on_volume_press

    print(f"Spotifoni controls active — volume encoder on GPIO {VOLUME_CLK}/{VOLUME_DT}, "
          f"button on GPIO {VOLUME_SW}")

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()
    print("Shutting down.")


if __name__ == "__main__":
    main()
