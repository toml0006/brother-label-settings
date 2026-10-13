#!/bin/bash
# Install the label printer's driver on a Mac, once. After that, adding the
# printer in System Settings offers it under "Use" next to AirPrint, and a
# queue added with it shows the printer's stored settings in the print dialog.
#
# The "driver" is one PPD file. macOS offers it for a printer whose advertised
# product name matches the file's *Product line, the same way it offers a
# vendor's driver once that vendor's package is installed.
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
echo "select Label Printer, and under Use choose \"Brother QL-1100 Label Print Server (macOS)\"."
