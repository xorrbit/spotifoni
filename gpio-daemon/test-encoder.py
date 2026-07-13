#!/usr/bin/env python3
"""Diagnostic: prints every rotary encoder event to stdout.

Run on the Pi with:  sudo python3 test-encoder.py
Stop with Ctrl-C.

If turning the volume dial produces no output, the issue is hardware/wiring.
If it does produce output, the issue is in the web API or Spotify volume path.
"""

import signal
import sys
import threading
import time

try:
    from gpiozero import RotaryEncoder, Button
except ImportError:
    print("gpiozero not available -- install with: sudo apt install python3-gpiozero")
    sys.exit(1)

VOLUME_CLK = 17
VOLUME_DT = 27
VOLUME_SW = 22

PREV_CLK = 5
PREV_DT = 6
PREV_SW = 13

PLAY_CLK = 23
PLAY_DT = 24
PLAY_SW = 25

NEXT_CLK = 12
NEXT_DT = 16
NEXT_SW = 26

ENCODERS = {
    "volume":    (VOLUME_CLK, VOLUME_DT, VOLUME_SW),
    "previous":  (PREV_CLK, PREV_DT, PREV_SW),
    "play":      (PLAY_CLK, PLAY_DT, PLAY_SW),
    "next":      (NEXT_CLK, NEXT_DT, NEXT_SW),
}


def make_rotate_handler(name, encoder):
    def handler():
        direction = "CW" if encoder.steps > 0 else "CCW"
        print(f"  [{name}] rotated {direction}  (steps={encoder.steps})")
        encoder.steps = 0
    return handler


def make_press_handler(name):
    def handler():
        print(f"  [{name}] button PRESSED")
    return handler


def main():
    print("Encoder diagnostic -- turn dials and press buttons, output appears below.")
    print("Stop with Ctrl-C.\n")

    for name, (clk, dt, sw) in ENCODERS.items():
        enc = RotaryEncoder(clk, dt, max_steps=0, wrap=False)
        btn = Button(sw, pull_up=True, bounce_time=0.05)
        enc.when_rotated = make_rotate_handler(name, enc)
        btn.when_pressed = make_press_handler(name)
        print(f"  {name:10s}  CLK={clk}  DT={dt}  SW={sw}  -- ready")

    print("\nListening...\n")

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()
    print("\nDone.")


if __name__ == "__main__":
    main()
