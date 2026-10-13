#!/usr/bin/env bash
# Turn a Raspberry Pi into a network print server for a USB Brother QL label
# printer: a shared CUPS queue (AirPrint), a web UI on port 9631, and the
# printer's stored settings in both.
#
# The steps are the configuration of a working Pi (Raspberry Pi OS based on
# Debian 13, CUPS 2.4, a QL-1100). This script as a whole has NOT been run on
# a fresh system: read it before running it, and expect to fix something.
#
#   sudo ./install.sh
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "run with sudo: sudo ./install.sh" >&2; exit 1; }

PRINTER_NAME="${PRINTER_NAME:-Label_Printer}"
BROTHER_MODEL="${BROTHER_MODEL:-QL-1100}"
WEB_PORT="${WEB_PORT:-9631}"
WEB_DIR="/opt/label-printer-web"
SERVICE_USER="${SERVICE_USER:-${SUDO_USER:-pi}}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$HERE")"

echo "== packages"
apt-get update -q
# cups-filters converts what AirPrint clients send (iOS sends image/urf)
apt-get install -y -q cups cups-client cups-filters avahi-daemon openssl \
    python3 python3-venv imagemagick

# ImageMagick refuses to read PDFs by default; the filter converts them
for policy in /etc/ImageMagick-6/policy.xml /etc/ImageMagick-7/policy.xml; do
    [[ -f "$policy" ]] && sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' "$policy"
done

echo "== brother_ql (the inventree fork knows the QL-1100)"
python3 -m venv /opt/brother-ql-venv
/opt/brother-ql-venv/bin/pip install --quiet "brother-ql-inventree==1.3"

# /dev/usb/lp0 belongs to group lp
usermod -aG lp,lpadmin "$SERVICE_USER"

echo "== CUPS queue"
install -m 0755 "$HERE/brother-ql-autofit" /usr/lib/cups/filter/brother-ql-autofit
cupsctl --share-printers
# The filter prints through brother_ql itself, so the queue's device is /dev/null
lpadmin -p "$PRINTER_NAME" -E -v file:///dev/null -P "$HERE/label-printer-autofit.ppd" \
    -D "Label Printer" -o printer-is-shared=true

echo "== TLS certificate Apple devices accept"
# CUPS makes itself a certificate valid for 10 years. Apple refuses any server
# certificate valid for more than 825 days: macOS pauses the queue with
# "cups-pki-invalid" and AirPrint from iOS fails without a message. Replace it
# with one certificate valid for 398 days. It has to be renewed before then:
# run this script again.
HOST="$(hostname)"
IP="$(hostname -I | awk '{print $1}')"
CERT="/etc/cups/ssl/$HOST.local"
if grep -qE '^#?CreateSelfSignedCerts\s' /etc/cups/cups-files.conf; then
    sed -i -E 's/^#?CreateSelfSignedCerts\s.*/CreateSelfSignedCerts No/' /etc/cups/cups-files.conf
else
    echo 'CreateSelfSignedCerts No' >> /etc/cups/cups-files.conf
fi
install -d -m 0700 -g lp /etc/cups/ssl
# 5184000 s = 60 days: keep a certificate that still has that long to run
if ! openssl x509 -in "$CERT.crt" -noout -checkend 5184000 >/dev/null 2>&1; then
    find /etc/cups/ssl -maxdepth 1 \( -name '*.crt' -o -name '*.key' \) -delete
    openssl req -x509 -newkey rsa:2048 -sha256 -days 398 -nodes \
        -keyout "$CERT.key" -out "$CERT.crt" -subj "/CN=$HOST.local" \
        -addext "subjectAltName=DNS:$HOST.local,DNS:$HOST,DNS:localhost${IP:+,IP:$IP}" \
        -addext "extendedKeyUsage=serverAuth" 2>/dev/null
    chmod 0644 "$CERT.crt"
    chmod 0600 "$CERT.key"
fi

# The Pi Zero 2 W's Wi-Fi stalls with power saving on, and the printer drops
# off the network until a reboot
if [[ -d /etc/NetworkManager/conf.d ]]; then
    printf '[connection]\nwifi.powersave = 2\n' > /etc/NetworkManager/conf.d/wifi-powersave-off.conf
    systemctl reload NetworkManager 2>/dev/null || true
fi

# Raspberry Pi OS keeps the journal in memory (a drop-in under /usr/lib with
# Storage=volatile), so a Pi that drops off the network and is power-cycled
# leaves no trace of why. Keep it on disk, capped to spare the SD card. Read
# the boot before this one with: journalctl -b -1
install -d -m 0755 /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=persistent\nSystemMaxUse=50M\n' > /etc/systemd/journald.conf.d/50-persistent.conf
systemctl restart systemd-journald
journalctl --flush

systemctl enable cups avahi-daemon
systemctl restart cups
systemctl start avahi-daemon

echo "== web UI"
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" "$WEB_DIR"
install -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0755 "$HERE/server.py" "$WEB_DIR/server.py"
install -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0644 "$HERE/index.html" "$WEB_DIR/index.html"
rm -rf "$WEB_DIR/brother_label_settings"
cp -r "$REPO/brother_label_settings" "$WEB_DIR/brother_label_settings"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$WEB_DIR/brother_label_settings"

cat > /etc/systemd/system/label-printer-web.service << EOF
[Unit]
Description=Label Printer Web Management UI
After=network.target cups.service
Requires=cups.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$WEB_DIR
Environment=WEB_PORT=$WEB_PORT
Environment=PRINTER_NAME=$PRINTER_NAME
Environment=BROTHER_MODEL=$BROTHER_MODEL
Environment="PRINTER_MODEL=Brother $BROTHER_MODEL"
ExecStart=/usr/bin/python3 $WEB_DIR/server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now label-printer-web

echo
echo "Web UI:  http://$(hostname).local:$WEB_PORT"
echo "Queue:   ipp://$(hostname).local:631/printers/$PRINTER_NAME"
echo "The web UI has no login. Keep this machine on a network you trust."
