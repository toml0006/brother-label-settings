#!/usr/bin/env bash
# Optional, for a Pi that does nothing but print: stop the services a print
# server does not use and keep them from starting. A Pi Zero 2 W has 416 MB of
# usable memory, and cups-browsed adds a local queue for every other printer
# on the network.
#
# Nothing is uninstalled. Each unit is masked; undo one with
#   sudo systemctl unmask <unit> && sudo systemctl enable --now <unit>
#
# Do not run this on a machine that does anything else: it turns off
# Bluetooth, mobile-broadband modems and the automatic mounting of USB disks.
#
#   sudo ./slim-down.sh
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "run with sudo: sudo ./slim-down.sh" >&2; exit 1; }

UNITS=(
    ModemManager.service   # no modem
    bluetooth.service
    cups-browsed.service   # local queues for other printers on the network
    colord.service         # colour profiles; labels are black and white
    udisks2.service        # automatic mounting of removable disks
    e2scrub_reap.service   # only useful with LVM snapshots; slow at boot
    e2scrub_all.timer
    man-db.timer
)

for unit in "${UNITS[@]}"; do
    systemctl list-unit-files "$unit" >/dev/null 2>&1 || continue   # not installed
    systemctl disable --now "$unit" 2>/dev/null || true
    systemctl mask "$unit"
done
# a timer masked while it was waiting is left marked as failed
systemctl reset-failed "${UNITS[@]}" 2>/dev/null || true

# cups-browsed normally removes its queues when it stops; remove any it left
for queue in $(lpstat -v 2>/dev/null | sed -n 's/^device for \([^:]*\): implicitclass:.*/\1/p'); do
    lpadmin -x "$queue"
done

echo "Still running:"
systemctl list-units --type=service --state=running --no-pager --no-legend | awk '{print "  " $1}'
