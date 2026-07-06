# Spotifoni - Antique Radio Modernization — Design Document

## Project Summary

Convert a Marconi 378 antique console radio into a modern streaming audio device while preserving the original exterior appearance. The unit will support Spotify Connect (appearing as a castable speaker in the Spotify app) and function as a Bluetooth speaker for any paired phone. The four original dials will be retrofitted with rotary encoders to provide physical controls for volume, transport, and power. Configuration will happen through a local web interface. The architecture leaves a clear upgrade path toward fully standalone Spotify playback in the future.


## Design Philosophy

The guiding principle is "invisible modernity." From the outside, this should look and feel like an untouched Marconi 378. Every component choice favors small footprint, low heat, and silence. The internal layout should be tidy enough that if someone opens the back, it looks intentional — not a rat's nest.


## Hardware Architecture

### Computing Platform — Raspberry Pi 3 Model B V1.2

The brain of the system is an existing Raspberry Pi 3 Model B V1.2. It has a quad-core Cortex-A53 at 1.2 GHz, 1 GB of RAM, 2.4 GHz WiFi, and Bluetooth Classic 4.1 with A2DP support — all built in. The 40-pin GPIO header provides I2S audio output, I2C for a future OLED display, and enough GPIO pins for four rotary encoders plus status LEDs. The board runs headless Raspberry Pi OS Lite with no issues.

1 GB of RAM is more than enough for the initial Spotify Connect + Bluetooth scope, and is also sufficient for the future standalone Spotify upgrade (spotifyd + Spotify Web API control layer + OLED UI). Only a heavier approach like running a full desktop browser in kiosk mode would strain it, and that's unlikely to be needed.

The board is credit-card sized (85×56 mm), which is larger than a Pi Zero but trivially small relative to the Marconi 378's console cabinet. It draws roughly 1.5–2.5W under typical load. A passive heatsink is a good idea inside the enclosed cabinet but active cooling is not needed at these workloads.


### Audio Output — MAX98357A I2S Mono Amp

The MAX98357A breakout board takes I2S digital audio directly from the Pi's GPIO header and outputs up to 3.2W into a 4Ω speaker. The signal stays digital all the way to the amplifier chip, avoiding the Pi's noisy built-in PWM audio jack entirely. The board is tiny (roughly 25×20 mm), needs no external components, and solders to five GPIO pins: LRCLK (GPIO 19), BCLK (GPIO 18), DIN (GPIO 21), VIN (5V), and GND.

At 3.2W into the 4Ω Visaton FR 10 HM, the system will produce approximately 90 dB SPL at one meter — more than enough to fill a living room from a console radio.


### Speaker — Visaton FR 10 HM, 4Ω

The original Marconi 378 speaker is an electro-dynamic field-coil loudspeaker with a 3.2Ω voice coil. Field-coil speakers require a separate DC power supply (typically 50–100+ volts) to energize the electromagnet — without it the speaker is completely dead. Rather than rebuilding that high-voltage supply chain, the original speaker is being replaced with a modern permanent magnet driver.

The Visaton FR 10 HM is a 4-inch (10 cm) full-range driver, 4Ω impedance, rated at 20W (max 30W). It has a paper cone with moisture-resistant coating and a small whizzer tweeter cone for extended high-frequency response (95 Hz – 22 kHz). Sensitivity is 85 dB at 1W/1m. The paper cone construction gives it a warm, natural character well-suited to the "antique radio playing modern music" aesthetic.

The Marconi 378's original speaker opening is significantly larger than 4 inches. An adapter ring (flat plywood, MDF, or 3D-printed ring) with the large outer diameter matching the cabinet's existing mounting holes and a smaller inner cutout for the FR 10 HM will be fabricated. Painted black, it disappears behind the grille cloth.

The original field-coil speaker will be preserved and stored in case of future restoration.


### Controls — KY-040 Rotary Encoders

Each of the four original dials will be mechanically coupled to a KY-040 incremental rotary encoder with a built-in push button. These output two quadrature signals (A and B channels) for rotation direction, plus a momentary switch signal when pressed. The KY-040 breakout boards include pull-up resistors, which simplifies wiring.

The mechanical coupling to the original dial shafts is the trickiest physical part of the build. Options include a flexible shaft coupler if the diameters match, a 3D-printed adapter sleeve, or mounting the encoder directly behind the dial and using a short section of silicone tubing as a flexible coupler. Standard encoder shafts are 6mm D-shaft; if the original dials are friction-fit, they may press directly onto the encoder shaft.

Control mapping:

Dial 1 (Volume): Rotate for volume up/down. Press to toggle mute or power standby. A dedicated toggle switch on the back panel for hard power on/off is the simpler alternative.

Dial 2 (Previous): Press to go to the previous track. Rotation can be mapped to seeking backward within a track, or left unmapped initially.

Dial 3 (Play/Pause): Press to toggle playback. Rotation can be mapped to switching between Spotify and Bluetooth input sources in the future.

Dial 4 (Next): Press to skip to the next track. Rotation can be mapped to seeking forward, or to playlist scrolling once the standalone upgrade is implemented.

Each encoder uses 3 GPIO pins (A, B, and switch), so four encoders need 12 GPIO pins. The Pi 3B has 26 usable GPIO pins, leaving plenty of room for the I2S bus (3 pins), I2C for a future OLED (2 pins), and several status LEDs.


### Status Display

For the initial build, a few simple LEDs tucked behind the tuner window or dial openings: a warm amber LED for power-on (mimicking a tube warmup glow), a blue LED for active Bluetooth connection, and a green LED for Spotify active/playing. Each needs one GPIO pin and one 330Ω resistor.

For the future upgrade, a small SSD1306 OLED (128×32 or 128×64 pixels) connects over I2C (two GPIO pins: SDA and SCL). It can display track name, artist, volume level, and input source, and fits behind the tuner dial window. Wire the I2C bus to a header or connector now so the OLED can be dropped in later without reopening the build.


### Power Supply

The Pi 3B draws up to 2.5W under load. The MAX98357A at full volume adds up to 3.2W. LEDs and encoders add negligible draw. Total worst-case system draw is roughly 8W, so a 5V/2.5A (12.5W) supply has comfortable margin.

A Mean Well IRM-15-5 (5V, 3A, 15W) or similar enclosed AC-DC module takes mains AC directly and outputs regulated 5V. It's compact, efficient, and designed to be built into equipment. Wire the radio's power cord to the AC input side. Add a fuse (1A slow-blow) on the mains input for safety.

The original radio's power cord should be replaced with a modern 3-prong grounded cord if the chassis is metal, or at minimum a polarized 2-prong cord. Old ungrounded cloth cords are a fire and shock hazard. An IEC C14 panel-mount inlet on the back panel is the cleanest approach — it looks professional and lets you use any standard computer power cord.


## Software Architecture

The entire software stack runs on Raspberry Pi OS Lite (64-bit, Bookworm), the headless, no-desktop variant. Everything is managed through systemd services and configured either by editing files over SSH or through the web interface.

### Operating System Setup

Flash Raspberry Pi OS Lite (64-bit) to a microSD card using the Raspberry Pi Imager. Pre-configure WiFi credentials (hardcoded for now) and enable SSH in the imager's settings before first boot. On first boot the Pi will connect to the network and be accessible via SSH. No monitor or keyboard needed at any point.

### Spotify Connect — raspotify

The `raspotify` package wraps librespot (an open-source Spotify Connect client written in Rust) into a Debian package with a systemd service. Install it, configure the audio backend to use the I2S DAC via ALSA, and it just works. The radio will appear as a named device (e.g., "Marconi 378") in the Spotify app on any phone or computer on the same network. Configuration lives in `/etc/raspotify/conf` — device name, audio backend, bitrate (320 kbps for premium accounts), initial volume, and normalization settings.

Raspotify also exposes playback events (track change, play, pause, volume change) that the control daemon can subscribe to for updating LEDs or a future OLED.

### Bluetooth A2DP Sink

The Pi 3B's built-in Bluetooth 4.1 radio, managed by BlueZ, acts as an A2DP audio sink (a Bluetooth speaker). The setup involves enabling the Bluetooth service, setting the Pi as discoverable and pairable, configuring an agent that auto-accepts pairing, and routing the Bluetooth audio through PipeWire to the same ALSA output as Spotify.

PipeWire handles the audio routing — it can mix multiple sources and switch between them. When Spotify Connect is active, it plays Spotify. When a phone connects via Bluetooth and plays audio, it plays that instead (or mixes, depending on configuration). Priority can be configured so Spotify Connect takes over when activated, or vice versa.

Auto-pairing with a trusted device list means pairing a phone once, and it reconnects automatically whenever the radio is powered on and the phone is in range.

### GPIO Control Daemon

A small Python service using `gpiozero` or `RPi.GPIO` (or `libgpiod` via the Python `gpiod` package for portability if the board is ever swapped). The daemon:

Reads the four rotary encoders and their push buttons via interrupts (not polling — important for responsiveness and low CPU usage). Translates encoder rotation into volume commands via `amixer` or PipeWire's `wpctl` for the volume dial. Translates button presses into MPRIS2 D-Bus commands for play/pause/next/previous — MPRIS2 is the standard Linux media player interface, and both raspotify and the Bluetooth audio player expose it, so the same button commands control whichever source is active. Drives the status LEDs (power, Bluetooth connected, playing state). Optionally drives a future SSD1306 OLED via the `luma.oled` Python library, displaying track metadata from MPRIS2.

This daemon runs as a systemd service that starts on boot.

### Web Configuration Interface

A lightweight Flask (Python) web server running on port 80. Accessible from any browser on the local network at `http://spotifoni.local/` (via mDNS/Avahi). It provides WiFi configuration (scan for networks, enter credentials, save to wpa_supplicant or NetworkManager), Spotify device name and audio settings, Bluetooth pairing management (list paired devices, remove pairings, toggle discoverability), system controls (restart services, reboot, shutdown safely), and optionally a simple volume slider and transport controls as a web remote.

For the initial build this can be very bare-bones — even a single page with a few forms. It grows naturally as features are added.

### Power Management

The Pi doesn't have a true hardware power switch — when power is cut, it just dies, which can corrupt the SD card over time. The simplest safe approach is to configure the filesystem as read-only using `overlayfs`. The root filesystem is mounted as a read-only overlay, with a writable tmpfs layer for runtime state. Configuration changes (via the web UI) temporarily remount the persistent layer as writable, write the change, and remount read-only. This is the standard approach for embedded Pi projects.

With a read-only filesystem, the back-panel power switch can just cut power directly. No shutdown sequence needed. The Pi 3B boots in about 15–20 seconds.


## Bill of Materials

| Component | Status | Approximate Cost |
|---|---|---|
| Raspberry Pi 3 Model B V1.2 | On hand | $0 |
| MAX98357A I2S Amp Breakout | Ordered | ~$6 |
| 4× KY-040 Rotary Encoders | Ordered | ~$6 |
| Visaton FR 10 HM, 4Ω | Ordered | ~$15 |
| Mean Well IRM-15-5 (5V 3A PSU) | To order | ~$10 |
| Status LEDs (3×) + 330Ω resistors | To order | ~$2 |
| MicroSD card (32 GB) | To order | ~$6 |
| IEC C14 power inlet | To order | ~$3 |
| Fuse holder + 1A slow-blow fuse | To order | ~$2 |
| Speaker adapter ring material (plywood/MDF) | To fabricate | ~$3 |
| Hook-up wire, connectors, standoffs, heat shrink | To order | ~$8 |
| SSD1306 128×32 OLED (optional, for future) | To order | ~$4 |

**Total: approximately $65 CAD** (less if parts are on hand; Pi is free since it's existing stock).


## Physical Integration Plan

Strip the Marconi 378's original internals (tube chassis, original transformer, original wiring). Preserve the original field-coil speaker (store for potential future restoration), the dial mechanisms, and all decorative elements. Document everything with photos before removing — reference original mounting positions.

Mount the Pi and amp board to a small piece of acrylic, plywood, or 3D-printed bracket that attaches to existing screw holes or standoffs inside the cabinet. Keep the microSD card slot accessible for reflashing.

Fabricate the speaker adapter ring: measure the original speaker cutout diameter, cut a ring from plywood or MDF with that outer diameter and a 4-inch (100mm) inner cutout for the FR 10 HM. Drill mounting holes for both the cabinet and the new speaker. Paint black.

Mount the rotary encoders behind the original dial positions. Measure the original shaft diameters and spacing, fabricate adapter couplers (3D-printed sleeves, flexible shaft couplers, or silicone tubing). If the original dials are friction-fit, they may press directly onto the 6mm encoder D-shafts.

Run the power cord through the original cord entry point. Mount the IEC C14 inlet on the back panel. Position the PSU module away from the audio components to minimize electrical noise.

Route wiring neatly with zip ties or cable lacing. Keep mains AC wiring physically separated from low-voltage DC signal wiring. Use JST connectors for serviceability so components can be disconnected without desoldering.


## Build Phases

**Phase 1 — Proof of Concept (on the bench, outside the radio)**

Get the Pi 3B running headless with SSH access. Install raspotify, confirm Spotify Connect works with the FR 10 HM connected via the MAX98357A. Set up Bluetooth A2DP sink and confirm phone audio plays through the same output. Write a basic GPIO script that reads one encoder and controls volume. Estimated time: one weekend.

**Phase 2 — Full Controls and Software**

Wire up all four encoders and the status LEDs on a breadboard. Write the full GPIO control daemon with MPRIS2 integration. Set up PipeWire for audio source switching. Build the basic web config interface. Configure read-only filesystem. Estimated time: one to two weekends.

**Phase 3 — Physical Integration**

Strip the radio. Fabricate the speaker adapter ring and encoder mounts. Build the internal component bracket. Transfer everything from the breadboard into the cabinet. Solder permanent connections or crimp JST connectors. Test everything in-cabinet, adjust LED brightness and encoder feel. Estimated time: one to two weekends depending on mechanical challenges.

**Phase 4 — Polish**

Tune the audio (EQ settings in PipeWire to compensate for the speaker and cabinet characteristics). Refine the web interface. Add the OLED if desired. Set up mDNS so the web UI is reachable at `marconi378.local`. Final cable management and cleanup.


## Future Upgrades

### Standalone Spotify (Software Only)

When ready to move beyond Spotify Connect to fully standalone playback (power on, press play, music plays without touching a phone), the hardware is already in place. Replace raspotify with `spotifyd`, which is a more feature-rich Spotify client that can be controlled programmatically. Write a control layer that uses the Spotify Web API (with an OAuth token stored on the device) to manage playback — load a saved playlist, resume last session, skip tracks. The rotary encoders gain new roles: one dial scrolls through playlists, another navigates tracks within a playlist. An SSD1306 OLED displays track info and playlist names. A phone is only needed for the initial OAuth login. The Pi 3B's 1 GB of RAM handles this comfortably.

### Board Swap

If more compute power is ever needed (unlikely for audio), the Pi 3B can be swapped for a Pi 4B or Pi 5 with no other hardware changes — same 40-pin GPIO header, same I2S pinout, same software stack. For an open-source hardware path, the BeaglePlay ($99, OSHW-certified, 2 GB RAM, 16 GB eMMC) is the strongest alternative, though it requires a USB Bluetooth dongle for A2DP since it only has BLE onboard.

### Audio Quality Upgrade

If the MAX98357A's audio quality ever feels limiting, swap it for a PCM5102A I2S DAC breakout (line-level output) feeding a separate higher-quality amplifier. The I2S pins on the Pi are the same, so it's a drop-in change on the digital side.

### Original Speaker Restoration

The Marconi 378's field-coil speaker could be brought back to life by building a DC power supply for the field coil (measure its resistance, provide appropriate voltage and current) and adding a 1Ω series resistor to bring the 3.2Ω voice coil impedance up to 4.2Ω for the MAX98357A. This is a rewarding side project for a rainy weekend but not required for the system to work.
