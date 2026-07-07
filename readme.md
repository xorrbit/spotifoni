# Spotifoni

Marconi 378 antique console radio converted into a Spotify Connect speaker and Bluetooth audio sink, powered by a Raspberry Pi 3B.

## Hardware

- Raspberry Pi 3 Model B V1.2
- MAX98357A I2S mono amplifier
- Visaton FR 10 HM 4Ω full-range speaker
- 4× KY-040 rotary encoders (volume, previous, play/pause, next)
- WS2812B RGB LED sticks (8 LEDs each, behind tuner window)
- 74AHCT125 level shifter for LED data signal

See [design.md](design.md) for the full design document and [wiring.md](wiring.md) for the wiring diagrams.

## Setup

### Prerequisites

Flash **Raspberry Pi OS Lite (64-bit, Bookworm)** to a microSD card using the Raspberry Pi Imager. In the imager settings, configure:
- WiFi credentials
- SSH enabled
- Username and password

### Provision

SSH into the Pi and update the system:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git
```

Clone the repo and run the setup script:

```bash
git clone https://github.com/xorrbit/spotifoni.git
cd spotifoni
sudo ./setup.sh
```

This installs all dependencies (raspotify, BlueZ, Python packages), deploys the application to `/opt/spotifoni`, configures I2S audio output, sets the hostname to `spotifoni`, and enables all systemd services.

Reboot after first run (required for the I2S DAC overlay):

```bash
sudo reboot
```

### Deploy Updates

After making changes on your dev machine, push them to the Pi without re-running the full setup:

```bash
./deploy.sh              # defaults to spotifoni.local
./deploy.sh 192.168.1.50 # or specify a host
```

This rsyncs the GPIO daemon and web app to the Pi and restarts both services.

## Usage

| What | Where |
|---|---|
| Spotify Connect | Open Spotify on any device, select **Marconi 378** as the playback device |
| Bluetooth | Pair your phone with **spotifoni** via Bluetooth settings |
| Web UI | `http://spotifoni.local/` — service status, volume, Bluetooth devices, system controls |
| SSH | `ssh pi@spotifoni.local` |

### Physical Controls

- **Volume dial** — rotate to adjust volume, press to toggle mute
- **Previous dial** — press for previous track
- **Play/Pause dial** — press to toggle playback
- **Next dial** — press for next track
