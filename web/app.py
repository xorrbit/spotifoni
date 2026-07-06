#!/usr/bin/env python3
"""Spotifoni web configuration interface."""

import os
import shutil
import subprocess
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DEV_MODE = os.environ.get("SPOTIFONI_DEV") == "1" or not os.path.exists("/sys/firmware/devicetree/base/model")

ASOUND_CONF = "/etc/asound.conf"
AUDIO_OUTPUTS = {
    "i2s": {"card": "sndrpihifiberry", "label": "I²S DAC (MAX98357A)"},
    "headphone": {"card": "Headphones", "label": "Headphone Jack"},
}

_mock_state = {
    "volume": 50,
    "services": {"raspotify": "active", "spotifoni-controls": "active", "bluetooth": "active"},
    "devices": [
        {"mac": "AA:BB:CC:DD:EE:01", "name": "Andrew's iPhone"},
        {"mac": "AA:BB:CC:DD:EE:02", "name": "Living Room Echo"},
    ],
    "audio_output": "headphone",
}


def run_cmd(cmd, check=False):
    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    return result.stdout.strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    if DEV_MODE:
        return jsonify({
            "hostname": "spotifoni-dev",
            "services": dict(_mock_state["services"]),
            "volume_raw": f"Mono: Playback [{_mock_state['volume']}%]",
        })

    services = {}
    for svc in ["raspotify", "spotifoni-controls", "bluetooth"]:
        out = run_cmd(["systemctl", "is-active", svc])
        services[svc] = out

    volume = run_cmd(["amixer", "sget", "Master"])
    hostname = run_cmd(["hostname"])

    return jsonify({
        "hostname": hostname,
        "services": services,
        "volume_raw": volume,
    })


@app.route("/api/volume", methods=["POST"])
def set_volume():
    level = request.json.get("level")
    if level is not None:
        if DEV_MODE:
            _mock_state["volume"] = int(level)
        else:
            run_cmd(["amixer", "sset", "Master", f"{int(level)}%"])
    return jsonify({"ok": True})


@app.route("/api/service/<name>/<action>", methods=["POST"])
def service_action(name, action):
    allowed_services = {"raspotify", "spotifoni-controls", "bluetooth"}
    allowed_actions = {"restart", "stop", "start"}
    if name not in allowed_services or action not in allowed_actions:
        return jsonify({"error": "not allowed"}), 400
    if DEV_MODE:
        if action == "stop":
            _mock_state["services"][name] = "inactive"
        else:
            _mock_state["services"][name] = "active"
        return jsonify({"ok": True})
    run_cmd(["sudo", "systemctl", action, name])
    return jsonify({"ok": True})


@app.route("/api/system/<action>", methods=["POST"])
def system_action(action):
    if action not in ("reboot", "shutdown"):
        return jsonify({"error": "unknown action"}), 400
    if DEV_MODE:
        return jsonify({"ok": True, "dev": f"{action} simulated"})
    if action == "reboot":
        subprocess.Popen(["sudo", "reboot"])
    else:
        subprocess.Popen(["sudo", "shutdown", "-h", "now"])
    return jsonify({"ok": True})


@app.route("/api/bluetooth/devices")
def bluetooth_devices():
    if DEV_MODE:
        return jsonify({"devices": list(_mock_state["devices"])})
    out = run_cmd(["bluetoothctl", "devices", "Paired"])
    devices = []
    for line in out.splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3:
            devices.append({"mac": parts[1], "name": parts[2]})
    return jsonify({"devices": devices})


def _current_audio_output():
    try:
        with open(ASOUND_CONF) as f:
            content = f.read()
        for key, out in AUDIO_OUTPUTS.items():
            if out["card"] in content:
                return key
    except FileNotFoundError:
        pass
    return "i2s"


def _set_audio_output(key):
    card = AUDIO_OUTPUTS[key]["card"]
    conf = (f"# /etc/asound.conf — managed by Spotifoni\n"
            f"# Current output: {key}\n\n"
            f"pcm.!default {{\n    type hw\n    card {card}\n}}\n\n"
            f"ctl.!default {{\n    type hw\n    card {card}\n}}\n")
    with open(ASOUND_CONF, "w") as f:
        f.write(conf)
    run_cmd(["sudo", "systemctl", "restart", "raspotify"])


@app.route("/api/audio/output")
def audio_output():
    if DEV_MODE:
        current = _mock_state["audio_output"]
    else:
        current = _current_audio_output()
    return jsonify({
        "current": current,
        "outputs": {k: v["label"] for k, v in AUDIO_OUTPUTS.items()},
    })


@app.route("/api/audio/output", methods=["POST"])
def set_audio_output():
    key = request.json.get("output")
    if key not in AUDIO_OUTPUTS:
        return jsonify({"error": "unknown output"}), 400
    if DEV_MODE:
        _mock_state["audio_output"] = key
    else:
        _set_audio_output(key)
    return jsonify({"ok": True, "current": key})


if __name__ == "__main__":
    port = 8080 if DEV_MODE else 80
    if DEV_MODE:
        print("Running in dev mode with mock data")
    app.run(host="0.0.0.0", port=port, debug=DEV_MODE)
