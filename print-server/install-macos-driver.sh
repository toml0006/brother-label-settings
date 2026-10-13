#!/bin/bash
# Install the label printer's driver on a Mac, once. After that it is listed
# under Use > Select Software... when the printer is added in System Settings,
# and a queue added with it shows the printer's stored settings in the print
# dialog.
#
# The "driver" is one PPD file. macOS does not select it automatically for the
# Pi's queue (seen on macOS 27): it lists the queue as "Bonjour Shared" and
# preselects "Generic PostScript Printer".
#
#   sudo ./install-macos-driver.sh
#   Undo: sudo rm "/Library/Printers/PPDs/Contents/Resources/Brother QL-1100 Label Print Server.gz"
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "run with sudo: sudo ./install-macos-driver.sh" >&2; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="/Library/Printers/PPDs/Contents/Resources/Brother QL-1100 Label Print Server.gz"

install -d -m 0755 "$(dirname "$DEST")"
gzip -c "$HERE/label-printer-macos.ppd" > "$DEST"
chmod 0644 "$DEST"

echo "Installed: $DEST"
echo "Now add the printer: System Settings > Printers & Scanners > Add Printer,"
echo "select Label Printer, and under Use choose Select Software... and then"
echo "\"Brother QL-1100 Label Print Server (macOS)\"."
