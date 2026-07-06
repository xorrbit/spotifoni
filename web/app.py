#!/usr/bin/env python3
"""Spotifoni web configuration interface."""

import subprocess
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


def run_cmd(cmd, check=False):
    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    return result.stdout.strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
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
        run_cmd(["amixer", "sset", "Master", f"{int(level)}%"])
    return jsonify({"ok": True})


@app.route("/api/service/<name>/<action>", methods=["POST"])
def service_action(name, action):
    allowed_services = {"raspotify", "spotifoni-controls", "bluetooth"}
    allowed_actions = {"restart", "stop", "start"}
    if name not in allowed_services or action not in allowed_actions:
        return jsonify({"error": "not allowed"}), 400
    run_cmd(["sudo", "systemctl", action, name])
    return jsonify({"ok": True})


@app.route("/api/system/<action>", methods=["POST"])
def system_action(action):
    if action == "reboot":
        subprocess.Popen(["sudo", "reboot"])
        return jsonify({"ok": True})
    elif action == "shutdown":
        subprocess.Popen(["sudo", "shutdown", "-h", "now"])
        return jsonify({"ok": True})
    return jsonify({"error": "unknown action"}), 400


@app.route("/api/bluetooth/devices")
def bluetooth_devices():
    out = run_cmd(["bluetoothctl", "devices", "Paired"])
    devices = []
    for line in out.splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3:
            devices.append({"mac": parts[1], "name": parts[2]})
    return jsonify({"devices": devices})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
