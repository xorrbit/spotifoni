#!/usr/bin/env python3
"""Spotifoni GPIO control daemon — reads four rotary encoders, controls volume and transport."""

import os
import signal
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leds

try:
    from gpiozero import RotaryEncoder, Button
except ImportError:
    print("gpiozero not available — install with: sudo apt install python3-gpiozero")
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

VOLUME_STEP = 5
DEBOUNCE_SEC = 0.3

last_press = {"volume": 0, "prev": 0, "play": 0, "next": 0}


def set_volume(delta):
    direction = f"{delta}%+" if delta > 0 else f"{abs(delta)}%-"
    subprocess.run(["amixer", "sset", "Master", direction],
                   capture_output=True, check=False)


def mpris_command(command):
    subprocess.run(
        ["dbus-send", "--print-reply", "--dest=org.mpris.MediaPlayer2.raspotify",
         "/org/mpris/MediaPlayer2", f"org.mpris.MediaPlayer2.Player.{command}"],
        capture_output=True, check=False)


def toggle_mute():
    subprocess.run(["amixer", "sset", "Master", "toggle"],
                   capture_output=True, check=False)


def debounced(key):
    now = time.monotonic()
    if now - last_press[key] < DEBOUNCE_SEC:
        return False
    last_press[key] = now
    return True


def on_volume_rotate(encoder):
    if encoder.steps > 0:
        set_volume(VOLUME_STEP)
    else:
        set_volume(-VOLUME_STEP)
    encoder.steps = 0


def on_volume_press():
    if debounced("volume"):
        toggle_mute()


def on_prev_press():
    if debounced("prev"):
        mpris_command("Previous")


def on_play_press():
    if debounced("play"):
        mpris_command("PlayPause")


def on_next_press():
    if debounced("next"):
        mpris_command("Next")


def main():
    vol_encoder = RotaryEncoder(VOLUME_CLK, VOLUME_DT, max_steps=0, wrap=False)
    vol_button = Button(VOLUME_SW, pull_up=True, bounce_time=0.05)
    vol_encoder.when_rotated = lambda: on_volume_rotate(vol_encoder)
    vol_button.when_pressed = on_volume_press

    prev_encoder = RotaryEncoder(PREV_CLK, PREV_DT, max_steps=0, wrap=False)
    prev_button = Button(PREV_SW, pull_up=True, bounce_time=0.05)
    prev_button.when_pressed = on_prev_press

    play_encoder = RotaryEncoder(PLAY_CLK, PLAY_DT, max_steps=0, wrap=False)
    play_button = Button(PLAY_SW, pull_up=True, bounce_time=0.05)
    play_button.when_pressed = on_play_press

    next_encoder = RotaryEncoder(NEXT_CLK, NEXT_DT, max_steps=0, wrap=False)
    next_button = Button(NEXT_SW, pull_up=True, bounce_time=0.05)
    next_button.when_pressed = on_next_press

    led_ok = leds.init()
    if led_ok:
        leds.set_all(40, 20, 0)
        leds.show()

    print("Spotifoni controls active:")
    print(f"  Volume:     GPIO {VOLUME_CLK}/{VOLUME_DT}/{VOLUME_SW}")
    print(f"  Previous:   GPIO {PREV_CLK}/{PREV_DT}/{PREV_SW}")
    print(f"  Play/Pause: GPIO {PLAY_CLK}/{PLAY_DT}/{PLAY_SW}")
    print(f"  Next:       GPIO {NEXT_CLK}/{NEXT_DT}/{NEXT_SW}")
    print(f"  WS2812:     {'active' if led_ok else 'not available'}")

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()
    leds.clear()
    print("Shutting down.")


if __name__ == "__main__":
    main()
