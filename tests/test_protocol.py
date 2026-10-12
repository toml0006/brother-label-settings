"""The protocol, the model table, the transport and the CLI, with no printer.

The QL-1100 bytes below were copied by hand from Brother's definition for that
model and confirmed against a real QL-1100, so a slip in the generated table
fails here.
"""
import errno
import os
import socket
import threading

import pytest

from brother_label_settings import MODELS, cli, protocol, transport
from fakes import FakePrinter

QL1100 = MODELS["QL-1100"]
PRE = "1B 40 1B 69 61 01"
POST_GET = "1B 69 61 FF"
POST_SET = "1B 7E 53 1B 69 61 FF"

# key: (get, reply size, value index, set without the value byte, values)
QL1100_BYTES = {
    "auto_power_off": ("1B 69 55 41 01 00", 32, 30, "1B 69 55 41 00 00",
                       [0x00, 0x06, 0x0C, 0x18, 0x30, 0x48]),
    "auto_power_on": ("1B 69 55 70 01", 32, 30, "1B 69 55 70 00", [0, 1]),
    "cut_mode": ("1B 69 58 63 31 00 00", 3, 2, "1B 69 58 63 32 01 00", [0, 1, 8]),
    "print_data_after_printing": ("1B 69 58 73 31 00 00", 3, 2,
                                  "1B 69 58 73 32 01 00", [1, 0]),
    "info_report": ("1B 69 58 6F 31 00 00", 3, 2, "1B 69 58 6F 32 01 00", [0, 1, 2, 3]),
    "serialize_mode": ("1B 69 58 4F 31 00 00", 3, 2, "1B 69 58 4F 32 01 00", [1, 0]),
    "command_mode": ("1B 69 55 61 01", 32, 30, "1B 69 55 61 00", [1, 0, 3]),
}

# what a real QL-1100 answered on 2026-10-12
REAL_32 = bytes.fromhex("80 20 42 34 43 30 00 00 00 00 66 0b 00 00 2e 00"
                        "00 99 f0 00 00 00 00 00 00 00 00 00 00 00 03 01")
REAL_3 = bytes.fromhex("01 00 08")


def h(text):
    return bytes.fromhex(text)


def test_the_ql1100_table_is_brothers():
    assert [s.key for s in QL1100.settings] == list(QL1100_BYTES)
    for key, (get, size, index, set_, values) in QL1100_BYTES.items():
        s = QL1100.setting(key)
        assert (s.get, s.reply_size, s.index, s.set) == (h(get), size, index, h(set_)), key
        assert sorted(s.choices) == sorted(values), key
    assert QL1100.report == h("1B 69 55 4E")
    assert QL1100.factory_reset == h("1B 69 55 5A")


@pytest.mark.parametrize("model", MODELS.values(), ids=lambda m: m.name)
def test_every_model_table_is_well_formed(model):
    keys = [s.key for s in model.settings]
    assert keys and len(keys) == len(set(keys))
    assert "auto_power_off" in keys
    assert model.factory_reset
    for s in model.settings:
        assert 0 <= s.index < s.reply_size
        assert s.choices and all(0 <= v <= 255 for v in s.choices)
        assert s.get != s.set
        # print options: one keyword per value, none clashing with "no change"
        assert len(s.choice_keywords()) == len(s.choices), s.key
        assert protocol.NO_CHANGE not in s.choice_keywords()
        assert all(k.isalnum() for k in s.choice_keywords()), s.key
        assert len(s.label) <= 39  # PPD translation strings


@pytest.mark.parametrize("model", MODELS.values(), ids=lambda m: m.name)
def test_every_model_round_trips_through_a_fake_printer(model):
    printer = FakePrinter(model)
    for s in model.settings:
        for value in s.choices:
            protocol.write_settings(printer, model, {s.key: value})
            assert protocol.read_settings(printer, model)[s.key] == value


def test_read_wraps_the_gets_in_the_preamble_and_closing_command():
    printer = FakePrinter(QL1100, auto_power_off=0x18, cut_mode=8)
    values = protocol.read_settings(printer, QL1100)
    assert values["auto_power_off"] == 0x18
    assert values["cut_mode"] == 8
    assert printer.writes[0] == h(PRE)
    assert printer.writes[-1] == h(POST_GET)
    assert printer.writes[1:-1] == [h(v[0]) for v in QL1100_BYTES.values()]


def test_real_replies_parse():
    command_mode, cut = QL1100.setting("command_mode"), QL1100.setting("cut_mode")

    class Canned:
        def __init__(self, reply):
            self.reply, self.asked = reply, False

        def write(self, data):
            self.asked = True

        def read(self, size, timeout=None):
            if not self.asked:
                return b""
            out, self.reply = self.reply[:size], self.reply[size:]
            return out

    assert protocol._query(Canned(REAL_32), command_mode) == 0x03
    assert protocol._query(Canned(REAL_3), cut) == 0x08


def test_a_reply_left_unread_by_another_program_is_discarded():
    # seen on the hardware: one stale status packet shifted every later reply
    printer = FakePrinter(QL1100, auto_power_on=1, cut_mode=8)
    printer.pending = REAL_32
    values = protocol.read_settings(printer, QL1100)
    assert (values["auto_power_on"], values["cut_mode"]) == (1, 8)
    assert None not in values.values()


def test_a_32_byte_reply_without_the_status_header_is_no_answer():
    class Garbage:
        def write(self, data):
            self.reply = bytes(32)

        def read(self, size, timeout=None):
            out, self.reply = getattr(self, "reply", b"")[:size], b""
            return out

    assert protocol._query(Garbage(), QL1100.setting("auto_power_off")) is None


def test_disabling_auto_power_off_sends_brothers_bytes():
    printer = FakePrinter(QL1100, auto_power_off=0x06)
    protocol.write_settings(printer, QL1100, {"auto_power_off": 0})
    assert printer.writes == [h(PRE), h("1B 69 55 41 00 00 00"), h(POST_SET)]
    assert protocol.read_settings(printer, QL1100)["auto_power_off"] == 0


@pytest.mark.parametrize("changes", [
    {"auto_power_off": 5},        # a value this model's tool does not offer
    {"auto_power_off": 6.0},
    {"auto_power_off": "0"},
    {"nonsense": 0},
    {"print_density_1": 0},       # another model's setting
    {"cut_mode": 1, "auto_power_off": 999},
])
def test_an_invalid_change_sends_nothing(changes):
    printer = FakePrinter(QL1100)
    with pytest.raises(ValueError):
        protocol.write_settings(printer, QL1100, changes)
    assert printer.writes == []


def test_a_printer_that_does_not_answer_reads_as_none():
    printer = FakePrinter(QL1100)
    printer.silent = True
    values = protocol.read_settings(printer, QL1100)
    assert set(values.values()) == {None}
    assert printer.writes[-1] == h(POST_GET)


def test_print_report_is_one_write_and_absent_where_the_model_has_none():
    printer = FakePrinter(QL1100)
    protocol.print_report(printer, QL1100)
    assert printer.writes == [h(PRE + "1B 69 55 4E" + POST_GET)]
    with pytest.raises(ValueError):
        protocol.print_report(FakePrinter(MODELS["QL-800"]), MODELS["QL-800"])


def test_job_options_name_the_settings_to_change():
    options = ("PageSize=102x152 QLAutoPowerOff=Never QLCutMode=NoChange QLCommandMode=Bogus "
               "XQLAutoPowerOn=On job-uuid=urn:uuid:1 QLSerializeMode=ContinueFromLastNumber")
    assert protocol.changes_from_job_options(QL1100, options) == {
        "auto_power_off": 0, "serialize_mode": 1}
    assert protocol.changes_from_job_options(QL1100, "PageSize=102x152 copies=2") == {}


def test_signed_values_get_distinct_option_keywords():
    density = MODELS["QL-800"].setting("print_density_1").choice_keywords()
    assert (density["Minus2"], density["0"], density["Plus2"]) == (0xFE, 0x00, 0x02)


def test_device_id_gives_the_model():
    text = b"MFG:Brother;CMD:PT-CBP;MDL:QL-1100;CLS:PRINTER;"
    raw = (len(text) + 2).to_bytes(2, "big") + text + bytes(64)
    assert transport.parse_device_id(raw) == "QL-1100"
    assert transport.parse_device_id(b"\x00\x02" + bytes(64)) is None


def test_usblp_read_collects_a_split_reply_and_times_out_short():
    ours, theirs = socket.socketpair()
    dev = transport.UsbLp.__new__(transport.UsbLp)
    dev.fd = ours.fileno()
    theirs.send(b"\x80\x20")
    threading.Timer(0.05, theirs.send, [b"B"]).start()
    assert dev.read(3, timeout=1) == b"\x80\x20B"
    assert dev.read(3, timeout=0.05) == b""
    ours.close()
    theirs.close()


def test_usblp_waits_out_a_busy_device(monkeypatch):
    real_open, calls = os.open, []

    def busy_twice(path, flags):
        calls.append(path)
        if len(calls) < 3:
            raise OSError(errno.EBUSY, "Device or resource busy")
        return real_open(os.devnull, flags)

    monkeypatch.setattr(transport.os, "open", busy_twice)
    with transport.UsbLp("/dev/usb/lp0"):
        pass
    assert len(calls) == 3

    def always_busy(path, flags):
        raise OSError(errno.EBUSY, "Device or resource busy")

    monkeypatch.setattr(transport.os, "open", always_busy)
    with pytest.raises(OSError):
        transport.UsbLp("/dev/usb/lp0", busy_wait=0.2)


def test_cli_lists_models_and_ppd_options_without_a_printer(capsys):
    cli.main(["models"])
    out = capsys.readouterr().out
    assert all(name in out for name in MODELS)
    cli.main(["--model", "QL-1100", "ppd-options"])
    assert capsys.readouterr().out == protocol.ppd_options(QL1100)


def test_cli_leaves_the_printer_alone_for_a_job_without_setting_options():
    # the device does not exist: opening it would exit with an error
    cli.main(["--device", "/nonexistent", "apply-job-options", "PageSize=102x152"])
    with pytest.raises(SystemExit):
        cli.main(["--device", "/nonexistent", "apply-job-options", "QLAutoPowerOff=Never"])


def test_cli_rejects_an_unknown_model(monkeypatch):
    printer = FakePrinter(QL1100)
    monkeypatch.setattr(cli, "UsbLp", lambda path: printer)
    with pytest.raises(SystemExit, match="no settings table"):
        cli.main(["--model", "QL-9999", "show"])
    assert printer.writes == []


def test_cli_asks_the_printer_for_its_model(monkeypatch, capsys):
    printer = FakePrinter(MODELS["QL-800"], auto_power_off=3)
    monkeypatch.setattr(cli, "UsbLp", lambda path: printer)
    cli.main(["set", "auto_power_off=0"])
    out = capsys.readouterr().out
    assert out.startswith("# QL-800") and "Never (0x00)" in out
    assert printer.values["auto_power_off"] == 0
