"""Spotify Web API client for standalone playback."""

import json
import os
import re
import subprocess
import time

DEV_MODE = False

SCOPES = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
DEVICE_NAME = "Marconi 378"

_PROD_CONFIG_PATH = "/opt/spotifoni/config/spotify_api.json"
_PROD_CACHE_PATH = "/opt/spotifoni/data/.spotify_cache"
_DEV_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "spotify_api.json")
_DEV_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", ".spotify_cache")


def _config_path():
    return _DEV_CONFIG_PATH if DEV_MODE else _PROD_CONFIG_PATH


def _cache_path():
    return _DEV_CACHE_PATH if DEV_MODE else _PROD_CACHE_PATH


def load_config():
    try:
        with open(_config_path()) as f:
            cfg = json.load(f)
        if cfg.get("client_id") and cfg.get("client_secret"):
            return cfg
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return None


def _get_oauth_manager():
    cfg = load_config()
    if not cfg:
        return None
    from spotipy.oauth2 import SpotifyOAuth
    from spotipy.cache_handler import CacheFileHandler
    cache_dir = os.path.dirname(_cache_path())
    os.makedirs(cache_dir, exist_ok=True)
    return SpotifyOAuth(
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        redirect_uri=cfg.get("redirect_uri", "http://spotifoni.local/api/spotify/callback"),
        scope=SCOPES,
        cache_handler=CacheFileHandler(cache_path=_cache_path()),
    )


def get_auth_url():
    if DEV_MODE:
        return None
    oauth = _get_oauth_manager()
    if not oauth:
        return None
    return oauth.get_authorize_url()


def handle_callback(code):
    if DEV_MODE:
        return True
    oauth = _get_oauth_manager()
    if not oauth:
        return "Spotify API not configured"
    try:
        oauth.get_access_token(code)
        return True
    except Exception as e:
        return str(e)


def get_client():
    if DEV_MODE:
        return None
    oauth = _get_oauth_manager()
    if not oauth:
        return None
    token_info = oauth.cache_handler.get_cached_token()
    if not token_info:
        return None
    import spotipy
    return spotipy.Spotify(auth_manager=oauth)


def get_status():
    cfg = load_config()
    if DEV_MODE:
        return {"authenticated": True, "user": "dev_user", "config_present": cfg is not None}
    if not cfg:
        return {"authenticated": False, "user": None, "config_present": False}
    sp = get_client()
    if not sp:
        return {"authenticated": False, "user": None, "config_present": True}
    try:
        me = sp.current_user()
        return {"authenticated": True, "user": me.get("display_name", me["id"]), "config_present": True}
    except Exception:
        return {"authenticated": False, "user": None, "config_present": True}


def parse_spotify_url(url):
    if not url or not isinstance(url, str):
        return None
    url = url.strip()

    m = re.match(r"^spotify:(playlist|album|track):([A-Za-z0-9]+)$", url)
    if m:
        return {"type": m.group(1), "uri": url}

    m = re.match(r"https?://open\.spotify\.com/(playlist|album|track)/([A-Za-z0-9]+)", url)
    if m:
        content_type = m.group(1)
        content_id = m.group(2)
        return {"type": content_type, "uri": f"spotify:{content_type}:{content_id}"}

    return None


def find_device(sp):
    try:
        devices = sp.devices()
        for d in devices.get("devices", []):
            if d.get("name") == DEVICE_NAME:
                return d
    except Exception:
        pass
    return None


def _restart_raspotify():
    subprocess.run(["sudo", "systemctl", "restart", "raspotify"],
                   capture_output=True, check=False)
    time.sleep(5)


def play_content(url):
    if DEV_MODE:
        parsed = parse_spotify_url(url)
        if not parsed:
            return {"error": "Invalid Spotify URL"}
        return {"ok": True, "dev": "playback simulated", "uri": parsed["uri"]}

    parsed = parse_spotify_url(url)
    if not parsed:
        return {"error": "Invalid Spotify URL. Paste a playlist, album, or track link from Spotify."}

    sp = get_client()
    if not sp:
        return {"error": "Spotify account not connected. Click Connect to set up."}

    device = find_device(sp)
    if not device:
        _restart_raspotify()
        device = find_device(sp)
    if not device:
        return {"error": f"Device \"{DEVICE_NAME}\" not found. Make sure raspotify is running and the device has been connected to your Spotify account at least once."}

    try:
        if parsed["type"] == "track":
            sp.start_playback(device_id=device["id"], uris=[parsed["uri"]])
        else:
            sp.start_playback(device_id=device["id"], context_uri=parsed["uri"])
        return {"ok": True}
    except Exception as e:
        msg = str(e)
        if "PREMIUM_REQUIRED" in msg or "403" in msg:
            return {"error": "Spotify Premium is required for standalone playback."}
        return {"error": f"Playback failed: {msg}"}


def disconnect():
    try:
        os.remove(_cache_path())
    except FileNotFoundError:
        pass
    return True
