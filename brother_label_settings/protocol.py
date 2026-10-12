"""Read and write a Brother label printer's stored settings.

Brother's Printer Setting Tool sends a preamble, then one command per setting,
then a closing command, each as its own write, and reads a fixed-size reply
after a "get". These functions do the same over any device object with
`write(data)` and `read(size, timeout=...)`.
"""
import re
from dataclasses import dataclass

READ_TIMEOUT = 1.0  # the tool waits 0.5 s; usblp on a Pi Zero is slower

# ESC @ (initialise), ESC i a 01 (raster command mode)
PRE = bytes.fromhex("1b40 1b696101")
POST_GET = bytes.fromhex("1b6961ff")
# ESC ~ S comes only after writes
POST_SET = bytes.fromhex("1b7e53 1b6961ff")

STATUS_HEADER = b"\x80\x20"

NO_CHANGE = "NoChange"


@dataclass(frozen=True)
class Setting:
    key: str
    label: str
    get: bytes
    set: bytes          # the value byte is appended
    reply_size: int
    index: int          # where the value sits in the reply
    choices: dict       # value byte -> label
    note: str = ""

    @property
    def option(self):
        """The print option's PPD keyword: auto_power_off -> QLAutoPowerOff."""
        return "QL" + _keyword(self.key.replace("_", " "))

    def choice_keywords(self):
        """PPD choice keyword -> value byte: "1 hour" -> 1Hour, "-2" -> Minus2."""
        return {_keyword(label): value for value, label in self.choices.items()}


@dataclass(frozen=True)
class Model:
    name: str
    settings: tuple
    report: bytes = None          # print the printer's own settings report
    factory_reset: bytes = None

    def setting(self, key):
        for s in self.settings:
            if s.key == key:
                return s
        raise ValueError(f"{self.name} has no setting {key!r}")


def _keyword(text):
    text = re.sub(r"^-(?=\d)", "Minus", re.sub(r"^\+(?=\d)", "Plus", text))
    return "".join(w[:1].upper() + w[1:] for w in re.split(r"[^A-Za-z0-9]+", text))


def _drain(dev, quiet):
    """Discard input until the printer has been silent for `quiet` seconds.

    A reply that an earlier program asked for and never read is delivered to
    the next reader, and would shift every reply after it.
    """
    while dev.read(64, timeout=quiet):
        pass


def _query(dev, setting):
    _drain(dev, 0.05)
    dev.write(setting.get)
    reply = dev.read(setting.reply_size, timeout=READ_TIMEOUT)
    if len(reply) < setting.reply_size:
        return None
    # a 32-byte reply is a status packet with the value in a spare byte
    if setting.reply_size == 32 and reply[:2] != STATUS_HEADER:
        return None
    return reply[setting.index]


def read_settings(dev, model):
    """Every setting's current value (None where the printer did not answer)."""
    dev.write(PRE)
    try:
        _drain(dev, 0.2)
        return {s.key: _query(dev, s) for s in model.settings}
    finally:
        dev.write(POST_GET)


def write_settings(dev, model, changes):
    """Store {key: value}. Raises ValueError before sending anything invalid."""
    for key, value in changes.items():
        choices = model.setting(key).choices
        if type(value) is not int or value not in choices:
            raise ValueError(f"{key}: {value!r} is not one of {sorted(choices)}")
    dev.write(PRE)
    try:
        for key, value in changes.items():
            dev.write(model.setting(key).set + bytes([value]))
    finally:
        dev.write(POST_SET)


def print_report(dev, model):
    """Print the printer's own settings report on the loaded labels."""
    if model.report is None:
        raise ValueError(f"{model.name} has no settings report")
    dev.write(PRE + model.report + POST_GET)


def factory_reset(dev, model):
    if model.factory_reset is None:
        raise ValueError(f"{model.name} has no factory reset command")
    dev.write(PRE + model.factory_reset + POST_GET)


def describe(model, values):
    """The settings and their values as JSON-ready rows, for a UI."""
    return [{
        "key": s.key,
        "label": s.label,
        "note": s.note,
        "value": values.get(s.key),
        "choices": [{"value": v, "label": l} for v, l in s.choices.items()],
    } for s in model.settings]


def ppd_options(model):
    """PPD lines that offer every setting as a print option (default: no change)."""
    out = ["*OpenGroup: QLSettings/Stored Printer Settings"]
    for s in model.settings:
        o = s.option
        out += [f"*OpenUI *{o}/{s.label}: PickOne",
                f"*OrderDependency: 20 AnySetup *{o}",
                f"*Default{o}: {NO_CHANGE}",
                f"*{o} {NO_CHANGE}/Don't change: \"\""]
        out += [f"*{o} {kw}/{s.choices[v]}: \"\""
                for kw, v in s.choice_keywords().items()]
        out += [f"*CloseUI: *{o}"]
    out.append("*CloseGroup: QLSettings")
    return "\n".join(out) + "\n"


def changes_from_job_options(model, options):
    """{key: value} for the settings a CUPS job's option string asks to change."""
    changes = {}
    for s in model.settings:
        m = re.search(rf"(?:^|\s){s.option}=(\S+)", options)
        if m and m.group(1) in s.choice_keywords():
            changes[s.key] = s.choice_keywords()[m.group(1)]
    return changes
