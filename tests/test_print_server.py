"""print-server/: the web server's settings routes and the PPDs, with no printer."""
import json
import pathlib
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import pytest

import brother_label_settings as bls
from fakes import FakePrinter

SERVER_DIR = pathlib.Path(__file__).resolve().parents[1] / "print-server"
sys.path.insert(0, str(SERVER_DIR))

import server  # noqa: E402

QL1100 = bls.MODELS["QL-1100"]
JSON = {"Content-Type": "application/json"}


@pytest.fixture
def web(monkeypatch):
    printer = FakePrinter(QL1100, auto_power_off=0x06)
    queue = {"jobs": ""}
    monkeypatch.setattr(bls, "UsbLp", lambda path: printer)
    monkeypatch.setattr(server.Handler, "_run", lambda self, cmd, **kw: queue["jobs"])
    httpd = server.ReusableTCPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(path, body=None, headers=JSON):
        req = urllib.request.Request(
            f"http://127.0.0.1:{httpd.server_address[1]}{path}",
            data=None if body is None else json.dumps(body).encode(),
            headers=headers if body is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, json.load(res), res.headers
        except urllib.error.HTTPError as e:
            return e.code, json.load(e), e.headers

    yield printer, queue, call
    httpd.shutdown()
    httpd.server_close()


def by_key(body):
    return {row["key"]: row for row in body["settings"]}


def test_reads_settings_for_the_model_the_printer_reports(web):
    printer, queue, call = web
    status, body, _ = call("/api/settings")
    assert status == 200 and body["ok"] and body["model"] == "QL-1100"
    row = by_key(body)["auto_power_off"]
    assert row["value"] == 0x06
    assert {"value": 0, "label": "Never"} in row["choices"]


def test_saves_and_answers_with_what_the_printer_now_reports(web):
    printer, queue, call = web
    status, body, _ = call("/api/settings", {"auto_power_off": 0})
    assert status == 200
    assert by_key(body)["auto_power_off"]["value"] == 0
    assert printer.values["auto_power_off"] == 0


def test_refuses_while_a_job_is_queued(web):
    printer, queue, call = web
    queue["jobs"] = "Label_Printer-12 someone 1024 Mon 12 Oct 2026\n"
    assert call("/api/settings")[0] == 409
    assert call("/api/settings", {"auto_power_off": 0})[0] == 409
    assert call("/api/action", {"action": "print_settings_report"})[0] == 409
    assert printer.writes == []


def test_rejects_a_bad_value_without_writing_it(web):
    printer, queue, call = web
    status, body, _ = call("/api/settings", {"auto_power_off": 7})
    assert status == 400 and not body["ok"]
    assert printer.values["auto_power_off"] == 0x06


def test_prints_the_report_without_reading_back(web):
    printer, queue, call = web
    status, body, _ = call("/api/action", {"action": "print_settings_report"})
    assert status == 200 and body["ok"]
    assert printer.writes == [bls.protocol.PRE + QL1100.report + bls.protocol.POST_GET]


@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded"])
def test_a_page_on_another_site_cannot_change_settings(web, content_type):
    # a browser sends these content types cross-site without asking first
    printer, queue, call = web
    status, body, headers = call("/api/settings", {"auto_power_off": 0},
                                 headers={"Content-Type": content_type})
    assert status == 415
    assert printer.writes == []
    assert headers.get("Access-Control-Allow-Origin") is None
    assert call("/api/action", {"action": "cancel_all"},
                headers={"Content-Type": content_type})[0] == 415


@pytest.mark.parametrize("ppd", ["label-printer-autofit.ppd", "label-printer-macos.ppd"])
def test_both_ppds_carry_the_packages_option_block(ppd):
    text = (SERVER_DIR / ppd).read_text()
    assert text.count("*OpenGroup: QLSettings") == 1
    assert bls.ppd_options(QL1100) in text


@pytest.mark.skipif(not shutil.which("cupstestppd"), reason="cupstestppd not installed")
def test_the_macos_ppd_passes_cupstestppd():
    run = subprocess.run(["cupstestppd", str(SERVER_DIR / "label-printer-macos.ppd")],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stdout
