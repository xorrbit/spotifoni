#!/usr/bin/env python3
"""Spotifoni GPIO control daemon — reads four rotary encoders, controls volume and transport."""

import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request

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

WEB_API = "http://127.0.0.1"

VOLUME_STEP = 2
VOLUME_TICKS_PER_STEP = 1
DEBOUNCE_SEC = 0.3

last_press = {"volume": 0, "prev": 0, "play": 0, "next": 0}
_vol_accum = 0
_vol_pending = 0
_vol_timer = None


def _web_post(path, data=None):
    import json as _json
    body = _json.dumps(data).encode() if data else b""
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(
        f"{WEB_API}{path}",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def _flush_volume():
    global _vol_pending
    if _vol_pending != 0:
        _web_post("/api/volume", {"delta": _vol_pending})
        _vol_pending = 0


def set_volume(delta):
    global _vol_pending, _vol_timer
    _vol_pending += delta
    if _vol_timer is not None:
        _vol_timer.cancel()
    _vol_timer = threading.Timer(0.2, _flush_volume)
    _vol_timer.start()


def transport_command(action):
    _web_post(f"/api/transport/{action}")


def toggle_mute():
    _web_post("/api/volume/mute")


def debounced(key):
    now = time.monotonic()
    if now - last_press[key] < DEBOUNCE_SEC:
        return False
    last_press[key] = now
    return True


def on_volume_rotate(encoder):
    global _vol_accum
    _vol_accum += encoder.steps
    encoder.steps = 0
    if abs(_vol_accum) >= VOLUME_TICKS_PER_STEP:
        set_volume(VOLUME_STEP if _vol_accum > 0 else -VOLUME_STEP)
        _vol_accum = 0


def on_volume_press():
    if debounced("volume"):
        toggle_mute()


def on_prev_press():
    if debounced("prev"):
        transport_command("previous")


def on_play_press():
    if debounced("play"):
        transport_command("play-pause")


def on_next_press():
    if debounced("next"):
        transport_command("next")


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
