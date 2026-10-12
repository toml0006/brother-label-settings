#!/bin/bash
# Add (or convert) the label printer queue on a Mac so that the print dialog
# shows the printer's stored settings (auto power off, cutter, ...).
#
# A driverless (AirPrint) queue cannot show them. This points the queue at the
# Pi's CUPS queue with label-printer-macos.ppd, which declares them as options;
# the Pi applies whatever a job carries before it prints.
#
# Usage: add-macos-printer.sh [queue-name] [device-uri]
#   An existing queue of that name keeps its device URI unless one is given.
#   Undo: delete the printer in System Settings and add it again.
set -euo pipefail

QUEUE="${1:-Label_Printer}"
PPD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/label-printer-macos.ppd"
CURRENT="$(lpstat -v "$QUEUE" 2>/dev/null | sed -n 's/^device for [^:]*: //p')"
URI="${2:-${CURRENT:-ipp://label-printer.local:631/printers/Label_Printer}}"

echo "Queue:  $QUEUE"
echo "Device: $URI"
echo "PPD:    $PPD"
lpadmin -p "$QUEUE" -v "$URI" -P "$PPD" -D "Label Printer" -E
echo "Done. Settings are under Printer Options > Stored Printer Settings in the print dialog."
