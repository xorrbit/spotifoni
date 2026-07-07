#!/usr/bin/env bash
#
# Spotifoni provisioning script
# Run on a fresh Raspberry Pi OS Lite (64-bit, Bookworm) install.
# Usage: ssh pi@spotifoni.local 'bash -s' < setup.sh
#    or: copy repo to Pi and run: sudo ./setup.sh

set -euo pipefail

SPOTIFONI_DIR="/opt/spotifoni"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Helpers ──────────────────────────────────────────────────────────────────

info()  { printf '\033[1;33m=> %s\033[0m\n' "$*"; }
err()   { printf '\033[1;31m!! %s\033[0m\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || err "Run as root: sudo ./setup.sh"

# ── System packages ──────────────────────────────────────────────────────────

info "Updating package lists"
apt-get update -qq

info "Installing dependencies"
apt-get install -y -qq \
    python3-gpiozero \
    python3-flask \
    python3-pip \
    bluez \
    alsa-utils \
    avahi-daemon \
    git

info "Installing WS2812B LED library"
pip3 install --break-system-packages rpi-ws281x

# ── Raspotify ────────────────────────────────────────────────────────────────

if ! command -v raspotify &>/dev/null; then
    info "Installing raspotify"
    curl -sL https://dtcooper.github.io/raspotify/install.sh | sh
else
    info "raspotify already installed"
fi

# ── Deploy application files ─────────────────────────────────────────────────

info "Deploying Spotifoni to ${SPOTIFONI_DIR}"
mkdir -p "${SPOTIFONI_DIR}"
rsync -a --delete \
    "${REPO_DIR}/gpio-daemon/" "${SPOTIFONI_DIR}/gpio-daemon/"
rsync -a --delete \
    "${REPO_DIR}/web/" "${SPOTIFONI_DIR}/web/"

# ── Configuration ────────────────────────────────────────────────────────────

info "Installing configuration files"
cp "${REPO_DIR}/config/raspotify.conf" /etc/raspotify/conf
cp "${REPO_DIR}/config/asound.conf" /etc/asound.conf

# I2S DAC overlay in boot config
BOOT_CONFIG="/boot/firmware/config.txt"
if ! grep -q "dtoverlay=hifiberry-dac" "${BOOT_CONFIG}" 2>/dev/null; then
    info "Enabling I2S DAC overlay in ${BOOT_CONFIG}"
    {
        echo ""
        echo "# Spotifoni — I2S DAC (MAX98357A)"
        echo "dtoverlay=hifiberry-dac"
    } >> "${BOOT_CONFIG}"
    NEEDS_REBOOT=1
else
    info "I2S DAC overlay already configured"
fi

# SPI for WS2812B LED strip
if ! grep -q "dtparam=spi=on" "${BOOT_CONFIG}" 2>/dev/null; then
    info "Enabling SPI for WS2812B LEDs in ${BOOT_CONFIG}"
    {
        echo ""
        echo "# Spotifoni — SPI for WS2812B LED strip"
        echo "dtparam=spi=on"
    } >> "${BOOT_CONFIG}"
    NEEDS_REBOOT=1
else
    info "SPI already enabled"
fi

# ── Hostname ─────────────────────────────────────────────────────────────────

DESIRED_HOSTNAME="spotifoni"
CURRENT_HOSTNAME="$(hostname)"
if [[ "${CURRENT_HOSTNAME}" != "${DESIRED_HOSTNAME}" ]]; then
    info "Setting hostname to ${DESIRED_HOSTNAME}"
    hostnamectl set-hostname "${DESIRED_HOSTNAME}"
    sed -i "s/${CURRENT_HOSTNAME}/${DESIRED_HOSTNAME}/g" /etc/hosts
fi

# ── Bluetooth A2DP ───────────────────────────────────────────────────────────

info "Configuring Bluetooth"
systemctl enable bluetooth
systemctl start bluetooth

# Make discoverable and pairable by default
mkdir -p /etc/bluetooth
if ! grep -q "DiscoverableTimeout = 0" /etc/bluetooth/main.conf 2>/dev/null; then
    cat >> /etc/bluetooth/main.conf <<'BTCONF'

# Spotifoni — stay discoverable and pairable
[General]
DiscoverableTimeout = 0
PairableTimeout = 0
Class = 0x200414
BTCONF
fi

# ── Systemd services ─────────────────────────────────────────────────────────

info "Installing systemd services"
cp "${REPO_DIR}/systemd/spotifoni-controls.service" /etc/systemd/system/
cp "${REPO_DIR}/systemd/spotifoni-web.service" /etc/systemd/system/

systemctl daemon-reload

systemctl enable raspotify
systemctl enable spotifoni-controls
systemctl enable spotifoni-web

info "Starting services"
systemctl restart raspotify
systemctl restart spotifoni-controls
systemctl restart spotifoni-web

# ── sudoers for web interface ────────────────────────────────────────────────

SUDOERS_FILE="/etc/sudoers.d/spotifoni-web"
if [[ ! -f "${SUDOERS_FILE}" ]]; then
    info "Configuring sudoers for web interface"
    cat > "${SUDOERS_FILE}" <<'SUDOERS'
# Allow the spotifoni-web service to manage services and reboot
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart raspotify
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart spotifoni-controls
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart bluetooth
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop raspotify
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop spotifoni-controls
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop bluetooth
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl start raspotify
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl start spotifoni-controls
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl start bluetooth
ALL ALL=(ALL) NOPASSWD: /usr/sbin/reboot
ALL ALL=(ALL) NOPASSWD: /usr/sbin/shutdown -h now
SUDOERS
    chmod 440 "${SUDOERS_FILE}"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

info "Spotifoni setup complete!"
echo ""
echo "  Web UI:     http://spotifoni.local/"
echo "  Spotify:    Look for 'Marconi 378' in your Spotify app"
echo "  SSH:        ssh pi@spotifoni.local"
echo ""

if [[ "${NEEDS_REBOOT:-}" == "1" ]]; then
    echo "  *** Reboot required for I2S DAC changes ***"
    echo "  Run: sudo reboot"
fi
