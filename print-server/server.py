#!/usr/bin/env python3
"""
HTTP server for the label print server's web management UI.

- Queries the printer for live status (media type, size, phase).
- Lists CUPS jobs.
- Accepts PDF uploads and submits them to CUPS (the CUPS filter handles
  conversion + sizing + USB I/O, so this process just needs CUPS access).
- Generates a test label PDF on the fly for the Test Print button.
- Reads and writes the printer's stored settings (auto power off, cutter, ...)
  through the brother_label_settings package.
"""
import http.server
import json
import os
import socket
import subprocess
import socketserver
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path

import brother_label_settings as bls
from brother_label_settings.cli import resolve_model

PORT = int(os.environ.get("WEB_PORT", 9631))
WEB_DIR = Path(__file__).parent
PRINTER_NAME = os.environ.get("PRINTER_NAME", "Label_Printer")
PRINTER_MODEL = os.environ.get("PRINTER_MODEL", "Brother QL-1100")
BROTHER_QL = "/opt/brother-ql-venv/bin/brother_ql"
BROTHER_MODEL = os.environ.get("BROTHER_MODEL", "QL-1100")
# empty: ask the printer which model it is
SETTINGS_MODEL = os.environ.get("SETTINGS_MODEL") or None
USB_DEVICE = os.environ.get("USB_DEVICE", "/dev/usb/lp0")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, fmt, *args):
        pass  # suppress access log noise

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/status":
            self._api_status()
        elif path == "/api/jobs":
            self._api_jobs()
        elif path == "/api/settings":
            self._api_settings()
        else:
            super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path != "/api/print" and not self._is_json():
            # a JSON content type cannot be sent cross-site without a CORS
            # preflight, which this server never grants
            self._json({"ok": False, "message": "Content-Type must be application/json"}, status=415)
        elif path == "/api/action":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            self._api_action(body)
        elif path == "/api/settings":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            self._api_settings(body)
        elif path == "/api/print":
            length = int(self.headers.get("Content-Length", 0))
            pdf_data = self.rfile.read(length)
            self._api_print(pdf_data)
        else:
            self.send_error(404)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _is_json(self):
        return self.headers.get("Content-Type", "").split(";")[0].strip() == "application/json"

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _run(self, cmd, stderr_to_stdout=False, timeout=10):
        try:
            stderr = subprocess.STDOUT if stderr_to_stdout else subprocess.DEVNULL
            return subprocess.check_output(cmd, stderr=stderr, text=True, timeout=timeout)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return ""

    def _printer_status(self):
        """Ask the printer for its current media + phase via brother_ql."""
        if not os.path.exists(USB_DEVICE):
            return {"connected": False, "reason": f"{USB_DEVICE} not present"}

        try:
            out = subprocess.check_output(
                [BROTHER_QL, "-b", "linux_kernel",
                 "-p", f"file://{USB_DEVICE}",
                 "-m", BROTHER_MODEL, "status"],
                stderr=subprocess.DEVNULL, text=True, timeout=5,
            )
        except subprocess.TimeoutExpired:
            return {"connected": False, "reason": "status request timed out"}
        except subprocess.CalledProcessError:
            return {"connected": False, "reason": "status request failed"}
        except OSError as e:
            return {"connected": False, "reason": f"cannot access {USB_DEVICE}: {e}"}

        result = {"connected": True}
        for line in out.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                result[key.strip().lower().replace(" ", "_")] = value.strip()
        return result

    def _submit_to_cups(self, pdf_data, title="Label"):
        """Write the PDF to a temp file and submit via `lp`."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_data)
            path = f.name
        try:
            result = subprocess.run(
                ["lp", "-d", PRINTER_NAME, "-t", title, path],
                capture_output=True, text=True, timeout=15,
            )
            ok = result.returncode == 0
            msg = (result.stdout or result.stderr).strip()
            return ok, msg
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def _build_test_pdf(self):
        """Generate a self-describing test label PDF sized for 4x6 (1164x1660 @ 300dpi)."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        subprocess.run(
            [
                "convert", "-density", "300",
                "-size", "1164x1660", "xc:white",
                "-fill", "none", "-stroke", "black", "-strokewidth", "6",
                "-draw", "rectangle 40,40 1124,1620",
                "-fill", "black", "-stroke", "none",
                "-gravity", "north",
                "-pointsize", "140", "-annotate", "+0+160", "TEST PRINT",
                "-pointsize", "64",  "-annotate", "+0+360", "Label Printer",
                "-pointsize", "56",  "-annotate", "+0+470", ts,
                "-gravity", "center",
                "-pointsize", "180", "-annotate", "+0+0", "HELLO",
                "-gravity", "south",
                "-pointsize", "52",  "-annotate", "+0+150", "If you can read this,",
                "-pointsize", "52",  "-annotate", "+0+80",  "the print server works.",
                path,
            ],
            check=True,
        )
        try:
            with open(path, "rb") as f:
                return f.read()
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # API endpoints
    # ------------------------------------------------------------------
    def _api_status(self):
        lpstat_p = self._run(["lpstat", "-p", PRINTER_NAME])
        enabled = "enabled" in lpstat_p.lower()
        idle = "idle" in lpstat_p.lower()

        lpstat_o = self._run(["lpstat", "-o", PRINTER_NAME])
        job_count = len([l for l in lpstat_o.splitlines() if l.strip()])

        uptime = self._run(["uptime", "-p"]).strip()
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                cpu_temp = round(int(f.read().strip()) / 1000, 1)
        except Exception:
            cpu_temp = None

        self._json({
            "printer": PRINTER_NAME,
            "printer_model": PRINTER_MODEL,
            "enabled": enabled,
            "idle": idle,
            "job_count": job_count,
            "uptime": uptime,
            "cpu_temp": cpu_temp,
            "printer_status": self._printer_status(),
        })

    def _api_jobs(self):
        raw = self._run(["lpstat", "-o", PRINTER_NAME, "-l"])
        jobs = []
        current = None
        for line in raw.splitlines():
            if line and not line.startswith((" ", "\t")):
                if current:
                    jobs.append(current)
                parts = line.split()
                current = {
                    "name": parts[0] if parts else "",
                    "user": parts[1] if len(parts) > 1 else "",
                    "size": parts[2] if len(parts) > 2 else "",
                    "submitted": " ".join(parts[3:]) if len(parts) > 3 else "",
                    "details": {},
                }
            elif current and ":" in line:
                k, _, v = line.partition(":")
                current["details"][k.strip()] = v.strip()
        if current:
            jobs.append(current)
        self._json(jobs)

    def _api_print(self, pdf_data):
        if not pdf_data:
            self._json({"ok": False, "message": "No PDF data received"}, status=400)
            return
        ok, msg = self._submit_to_cups(pdf_data, title="Web Upload")
        self._json({
            "ok": ok,
            "message": msg or ("Sent to CUPS" if ok else "Print failed"),
        }, status=200 if ok else 500)

    def _with_printer(self, fn, reread=True):
        """Run fn(device) and answer with the settings as they are afterwards.

        Refused while CUPS holds a job: these commands start with a printer
        reset, which must not land in the middle of a label.
        """
        if self._run(["lpstat", "-o", PRINTER_NAME]).strip():
            self._json({"ok": False, "message": "Printer is busy with a print job"}, status=409)
            return
        try:
            with bls.UsbLp(USB_DEVICE) as dev:
                model = resolve_model(SETTINGS_MODEL, dev)
                fn(dev, model)
                values = bls.read_settings(dev, model) if reread else None
        except ValueError as e:
            self._json({"ok": False, "message": str(e)}, status=400)
            return
        except OSError as e:
            self._json({"ok": False, "message": f"Cannot reach printer: {e}"}, status=503)
            return
        if values is None:
            self._json({"ok": True, "message": "Sent to printer"})
        else:
            self._json({"ok": True, "model": model.name,
                        "settings": bls.describe(model, values)})

    def _api_settings(self, changes=None):
        if changes is None:
            self._with_printer(lambda dev, model: None)
        elif not isinstance(changes, dict) or not changes:
            self._json({"ok": False, "message": "Expected {setting: value}"}, status=400)
        else:
            self._with_printer(lambda dev, model: bls.write_settings(dev, model, changes))

    def _api_action(self, body):
        action = body.get("action", "")
        if action == "enable":
            self._run(["cupsenable", PRINTER_NAME])
            self._run(["cupsaccept", PRINTER_NAME])
            self._json({"ok": True, "message": "Printer enabled"})
        elif action == "disable":
            self._run(["cupsdisable", PRINTER_NAME])
            self._json({"ok": True, "message": "Printer disabled"})
        elif action == "cancel_all":
            self._run(["cancel", "-a", PRINTER_NAME])
            self._json({"ok": True, "message": "All jobs cancelled"})
        elif action == "print_settings_report":
            self._with_printer(bls.print_report, reread=False)
        elif action == "test_print":
            try:
                pdf = self._build_test_pdf()
            except subprocess.CalledProcessError as e:
                self._json({"ok": False, "message": f"Could not build test PDF: {e}"}, status=500)
                return
            ok, msg = self._submit_to_cups(pdf, title="Test Print")
            self._json({
                "ok": ok,
                "message": msg or ("Test print sent" if ok else "Test print failed"),
            }, status=200 if ok else 500)
        else:
            self._json({"ok": False, "message": f"Unknown action: {action}"}, status=400)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True
    allow_reuse_port = True

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        super().server_bind()


if __name__ == "__main__":
    with ReusableTCPServer(("", PORT), Handler) as httpd:
        print(f"Web UI running at http://0.0.0.0:{PORT}", flush=True)
        httpd.serve_forever()
