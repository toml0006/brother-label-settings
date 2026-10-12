"""brother-label-settings: read and change a Brother label printer's stored settings.

    brother-label-settings show
    brother-label-settings set auto_power_off=0
    brother-label-settings models
"""
import argparse
import json
import sys

from . import protocol
from .models import MODELS
from .transport import DEFAULT_DEVICE, UsbLp


def _parse_assignment(text):
    key, sep, value = text.partition("=")
    if not sep:
        raise argparse.ArgumentTypeError(f"expected key=value, got {text!r}")
    try:
        return key, int(value, 0)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None


def resolve_model(name, dev=None):
    """The Model for `name`, or for whatever printer `dev` says it is."""
    if name is None:
        name = dev.model_name() if dev else None
        if name is None:
            raise ValueError("the printer did not report its model; pass --model")
    if name not in MODELS:
        raise ValueError(f"no settings table for {name!r}; known: {', '.join(sorted(MODELS))}")
    return MODELS[name]


def _show(model, values):
    print(f"# {model.name}")
    for s in model.settings:
        v = values[s.key]
        shown = "no reply" if v is None else f"{s.choices.get(v, 'unknown')} (0x{v:02x})"
        print(f"{s.key:28} {shown}")


def _list_models(name):
    for model in ([resolve_model(name)] if name else MODELS.values()):
        print(model.name)
        for s in model.settings:
            values = ", ".join(f"{v}={l}" for v, l in s.choices.items())
            print(f"  {s.key:28} {values}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="brother-label-settings",
                                description=__doc__.split("\n\n")[0])
    p.add_argument("--device", default=DEFAULT_DEVICE,
                   help=f"usblp device (default {DEFAULT_DEVICE})")
    p.add_argument("--model", help="e.g. QL-800 (default: ask the printer)")
    sub = p.add_subparsers(dest="cmd", required=True)
    show = sub.add_parser("show", help="read every setting")
    show.add_argument("--json", action="store_true")
    setp = sub.add_parser("set", help="write settings, e.g. auto_power_off=0")
    setp.add_argument("changes", nargs="+", type=_parse_assignment)
    sub.add_parser("models", help="list supported models, settings and values")
    sub.add_parser("print-report", help="print the printer's settings report")
    reset = sub.add_parser("factory-reset", help="restore factory settings")
    reset.add_argument("--yes", action="store_true", required=True)
    job = sub.add_parser("apply-job-options",
                         help="apply the QL* options in a CUPS option string")
    job.add_argument("options")
    sub.add_parser("ppd-options", help="print PPD lines offering the settings (needs --model)")
    args = p.parse_args(argv)

    try:
        if args.cmd == "models":
            return _list_models(args.model)
        if args.cmd == "ppd-options":
            return print(protocol.ppd_options(resolve_model(args.model)), end="")
        if args.cmd == "apply-job-options" and "QL" not in args.options:
            return  # the usual job: leave the printer alone

        with UsbLp(args.device) as dev:
            model = resolve_model(args.model, dev)
            if args.cmd == "apply-job-options":
                changes = protocol.changes_from_job_options(model, args.options)
                if not changes:
                    return
                protocol.write_settings(dev, model, changes)
            elif args.cmd == "set":
                protocol.write_settings(dev, model, dict(args.changes))
            elif args.cmd == "print-report":
                return protocol.print_report(dev, model)
            elif args.cmd == "factory-reset":
                return protocol.factory_reset(dev, model)
            values = protocol.read_settings(dev, model)
    except (OSError, ValueError) as e:
        sys.exit(f"error: {e}")
    if getattr(args, "json", False):
        print(json.dumps(protocol.describe(model, values), indent=2))
    else:
        _show(model, values)


if __name__ == "__main__":
    main()
