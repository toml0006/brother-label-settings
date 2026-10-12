# Raspberry Pi print server

Puts a USB Brother QL label printer on the network from a Raspberry Pi:

- a shared CUPS queue, so the printer shows up as an AirPrint printer on macOS
  and iOS and as a network printer elsewhere;
- a filter that trims a PDF or image to its content and scales it to the label;
- a web page on port 9631 with status, the job queue, a PDF upload, and the
  printer's stored settings;
- the same settings as options in the macOS print dialog.

It was built for a QL-1100 on a Pi Zero 2 W and has only run there.

## Install

```bash
git clone https://github.com/toml0006/brother-label-settings
cd brother-label-settings/print-server
sudo ./install.sh
```

`install.sh` is written from the configuration of the one Pi this runs on. The
script itself has not been run on a fresh system, so read it first.

For a model other than the QL-1100, run it as `sudo BROTHER_MODEL=QL-800
./install.sh` and change the default near the top of `brother-ql-autofit`. The
label sizes in the filter and the PPDs are the QL-1100's.

## The web page

`http://<hostname>.local:9631`. The **Printer Settings** card shows what the
printer reports and saves what you change. After a save it shows the values
read back from the printer, not the ones sent.

**There is no login.** Anyone who can reach port 9631 can change settings,
cancel jobs and print. Keep the Pi on a network you trust. The server only
accepts JSON requests and sends no cross-origin headers, so a web page on
another site cannot drive it through your browser.

Settings are refused while a job is in the queue.

## The macOS print dialog

A printer added through AirPrint cannot show these settings: its dialog is
built from standard attributes. Run this once on the Mac to switch its queue to
`label-printer-macos.ppd`:

```bash
./add-macos-printer.sh            # queue Label_Printer, keeps its current address
```

The dialog then has **Printer Options > Stored Printer Settings**, one menu per
setting, each on **Don't change**. Pick a value and print a label: the Pi
applies the setting, then prints. The printer remembers it. The dialog cannot
show the printer's current values; the web page does.

Checked: macOS 27 accepts the PPD and lists the options. Not checked: a job
carrying an option from a Mac through to the printer.

The same options work from any CUPS client:
`lp -d Label_Printer -o QLAutoPowerOff=Never label.pdf`.

## Files

| File | Where it goes on the Pi |
|---|---|
| `server.py`, `index.html` | `/opt/label-printer-web/` |
| `../brother_label_settings/` | `/opt/label-printer-web/brother_label_settings/` |
| `brother-ql-autofit` | `/usr/lib/cups/filter/` |
| `label-printer-autofit.ppd` | the queue's PPD |
| `label-printer-macos.ppd`, `add-macos-printer.sh` | used on the Mac |

The filter prints through [brother_ql](https://github.com/matmair/brother_ql-inventree)
itself, so the CUPS queue's device is `/dev/null`. Its log is
`/tmp/brother-ql-autofit.log`.
