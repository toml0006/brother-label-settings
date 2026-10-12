# brother-label-settings

Read and change the settings stored inside Brother QL and PT label printers,
from Linux, over USB. The setting most people come for is **auto power off**:
the printer turns itself off after a while, and the only official way to stop
that is Brother's Printer Setting Tool on Windows or macOS.

```console
$ brother-label-settings show
# QL-1100
auto_power_off               4 hours (0x18)
auto_power_on                Off (0x00)
cut_mode                     Cut after each label (0x01)
print_data_after_printing    Keep (0x00)
info_report                  All (0x03)
serialize_mode               Continue from last number (0x01)
command_mode                 P-touch Template (0x03)

$ brother-label-settings set auto_power_off=0
# QL-1100
auto_power_off               Never (0x00)
...
```

The repository also holds a [Raspberry Pi print server](print-server/) for
these printers, with a web page for the settings and the same settings in the
macOS print dialog.

This project is not affiliated with or endorsed by Brother Industries.

## What has been tested

**Only the QL-1100 has been tested on a real printer.** Every other model's
table comes from the same source and has the same shape, but nobody has run it
against the hardware yet.

| | Status |
|---|---|
| QL-1100, reading all 7 settings | Tested on hardware |
| QL-1100, writing | Auto power off and power-on were changed through the print server's web page and read back correctly. The other five settings have not been written. |
| QL-1100, settings report and factory reset | Not tested |
| QL-600, QL-800, QL-810W, QL-820NWB, QL-1110NWB | Not tested |
| PT-D800W, PT-E800W, PT-P710BT, PT-P715eBT, PT-P900W, PT-P910BT, PT-P950NW | Not tested |
| TP-M5000N | Not tested |

If you have one of the untested models, `show` only reads, so it is the safe
first step. Please open an issue with the output either way, working or not.

## Install

Linux with the kernel's `usblp` driver (it is what creates `/dev/usb/lp0`),
Python 3.9 or newer, no dependencies.

```bash
pip install git+https://github.com/toml0006/brother-label-settings
```

Your user needs to be in the group that owns `/dev/usb/lp0`, usually `lp`:
`sudo usermod -aG lp $USER`, then log in again.

## Use

```bash
brother-label-settings show                    # read everything
brother-label-settings show --json
brother-label-settings set auto_power_off=0    # one or more key=value pairs
brother-label-settings models                  # every model, setting and value
brother-label-settings --model QL-800 models   # one model
brother-label-settings print-report            # prints on the loaded labels
brother-label-settings factory-reset --yes
```

The printer is asked which model it is. `--model QL-800` overrides that, and
`--device` picks a device other than `/dev/usb/lp0`.

Values are the numbers `models` lists, in decimal or hex (`0x18`). A value the
model's table does not list is refused before anything is sent.

Do not run it while a job is printing: every exchange starts by resetting the
printer's command state.

## Models and settings

| Model | Settings | Settings report |
|---|---|---|
| QL-600 | `auto_power_off`, `auto_power_on`, `print_data_after_printing` | no |
| QL-800 | `auto_power_off`, `auto_power_on`, `print_density_1`, `print_density_2`, `print_data_after_printing` | no |
| QL-810W | `auto_power_off`, `auto_power_off_battery`, `auto_power_on`, `print_density_1`, `print_density_2`, `battery_charge_limit`, `print_data_after_printing`, `info_report`, `command_mode` | yes |
| QL-820NWB | `auto_power_off`, `auto_power_off_battery`, `auto_power_on`, `print_density_1`, `print_density_2`, `battery_charge_limit`, `print_data_after_printing`, `info_report`, `command_mode` | yes |
| QL-1100 | `auto_power_off`, `auto_power_on`, `cut_mode`, `print_data_after_printing`, `info_report`, `serialize_mode`, `command_mode` | yes |
| QL-1110NWB | `auto_power_off`, `auto_power_on`, `cut_mode`, `print_data_after_printing`, `info_report`, `serialize_mode`, `command_mode` | yes |
| PT-D800W, PT-E800W, PT-P900W, PT-P950NW | `auto_power_off`, `auto_power_off_battery`, `auto_power_on`, `length_adjustment`, `full_cut_margin`, `half_cut_margin`, `info_report`, `save_print_log` | yes |
| PT-P710BT, PT-P715eBT | `auto_power_off`, `auto_power_off_battery`, `auto_power_on`, `length_adjustment`, `info_report` | yes |
| PT-P910BT | `auto_power_off`, `auto_power_off_battery`, `auto_power_on`, `length_adjustment`, `full_cut_margin`, `half_cut_margin`, `special_tape_feed`, `info_report` | yes |
| TP-M5000N | `auto_power_off`, `print_position` | no |

The same setting name can mean different commands and different values on
different models: `auto_power_off` goes up to 12 hours on a QL-1100 and to one
hour on a QL-800. `brother-label-settings models` prints the exact values.

Not covered: Wi-Fi and Bluetooth settings on any model, and the PJ mobile
printers, which use other mechanisms.

## From Python

```python
from brother_label_settings import MODELS, UsbLp, read_settings, write_settings

model = MODELS["QL-1100"]
with UsbLp("/dev/usb/lp0") as printer:
    write_settings(printer, model, {"auto_power_off": 0})
    print(read_settings(printer, model))
```

`read_settings` and `write_settings` take any object with `write(data)` and
`read(size, timeout=...)`, so another transport is a small class.

## Limits

- Linux and USB only. The network-capable models are not reachable over the
  network with this.
- One program can hold `/dev/usb/lp0` at a time. If something else is talking
  to the printer, opening it waits up to three seconds and then fails.
- An unlisted value is refused. Whether a printer accepts values between the
  listed ones (a 30-minute timeout on a QL-1100, say) is unknown.

## How the commands were found

Brother's Printer Setting Tool carries one definition per printer model: for
each setting, a command that reads it, a command that writes it, and the values
it can take. The tables in [`models.py`](brother_label_settings/models.py) hold
those commands and values, with this project's own names.
[docs/PROTOCOL.md](docs/PROTOCOL.md) describes the exchange and what a real
QL-1100 sends back.

None of Brother's files, text or code is included here.

## Development

```bash
pip install pytest
python -m pytest
```

The tests use a fake printer and need no hardware.

## License

MIT. See [LICENSE](LICENSE).
