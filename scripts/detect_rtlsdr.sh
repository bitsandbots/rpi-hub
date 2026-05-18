#!/usr/bin/env bash
# Purpose: Print "present" + exit 0 if a known RTL-SDR USB dongle is
#          plugged in; print "absent" + exit 1 otherwise. install.sh
#          calls this to gate the dump1090-mutability enablement
#          step (Phase 8.4) so we don't enable an ADS-B receiver on a
#          headless image that has no radio attached.
# Unit:    n/a (install-time helper)
# Phase:   8.4 (introduced v1.2.1)
#
# Detection works by matching the USB vendor + product IDs that the
# Realtek RTL2832U demodulator chip ships under. The list below covers
# every dongle that the rtl-sdr library will actually claim — adding
# entries is safe because no other chip uses these IDs in the wild.
# References: github.com/osmocom/rtl-sdr librtlsdr/src/librtlsdr.c
#             known_devices[] table.

set -euo pipefail

# VID:PID combos that librtlsdr claims at probe time.
RTLSDR_IDS=(
    "0bda:2832"  # Realtek RTL2832U DVB-T (generic)
    "0bda:2838"  # Realtek RTL2832U + R820T / R820T2 — the SDR Blog v3/v4
    "0413:6680"  # Leadtek WinFast DTV Dongle Mini
    "0458:707f"  # KWorld USB2.0 DVB-T CT Stick HD
    "1554:5020"  # PixelView SBTVD
    "15f4:0131"  # HanfTek ASTROMETA DVB-T2 (RTL2832P)
    "1b80:d3a4"  # Twintech UT-40
    "1d19:1101"  # Dexatek DK DVB-T USB Dongle (Logilink VG0002A)
    "1d19:1102"  # Dexatek DK DVB-T USB Dongle (MSI DigiVox mini II V3)
    "1d19:1103"  # Dexatek Technology Ltd. DK 5217 DVB-T Dongle
    "1f4d:b803"  # GTek T803
    "1f4d:c803"  # Lifeview LV5TDeluxe
)

main() {
    if ! command -v lsusb >/dev/null 2>&1; then
        # usbutils not installed → can't tell. Treat as absent rather
        # than crashing the install.
        echo "absent"
        return 1
    fi

    local usb_output
    usb_output="$(lsusb)" || {
        echo "absent"
        return 1
    }

    local id
    for id in "${RTLSDR_IDS[@]}"; do
        if grep -qiF "ID ${id}" <<< "$usb_output"; then
            echo "present"
            return 0
        fi
    done

    echo "absent"
    return 1
}

main "$@"
