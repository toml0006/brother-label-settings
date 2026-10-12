"""Which settings each printer model has, and the bytes that read and write them.

Each row is one setting as one group of models implements it: the same
setting often has a different command or different values on another model.
The command and value bytes were recovered from the per-model definitions in
Brother's Printer Setting Tool 1.3.5 for macOS; see docs/PROTOCOL.md. The
names and labels are this project's own."""
from .protocol import Model, Setting

# key, label, get, set (the value byte is appended), reply size, value index,
# {value byte: label}, models, note
_ROWS = [
    ('auto_power_off', 'Auto power off (AC adapter)', '1b6955410100', '1b6955410000', 3, 2,
     {0x00: 'Never', 0x01: '10 minutes', 0x02: '20 minutes', 0x03: '30 minutes', 0x04: '40 minutes', 0x05: '50 minutes', 0x06: '1 hour', 0x07: '2 hours', 0x08: '4 hours', 0x09: '8 hours', 0x0A: '12 hours'},
     'PT-D800W PT-E800W PT-P900W PT-P950NW', ''),
    ('auto_power_off', 'Auto power off', '1b6955410101', '1b6955410001', 32, 30,
     {0x00: 'Never', 0x01: '10 minutes', 0x02: '20 minutes', 0x03: '30 minutes', 0x04: '40 minutes', 0x05: '50 minutes', 0x06: '1 hour'},
     'PT-P710BT PT-P715eBT', ''),
    ('auto_power_off', 'Auto power off (USB power)', '1b6955410100', '1b6955410000', 3, 2,
     {0x00: 'Never', 0x01: '10 minutes', 0x02: '20 minutes', 0x03: '30 minutes', 0x04: '40 minutes', 0x05: '50 minutes', 0x06: '1 hour', 0x0C: '2 hours', 0x18: '4 hours', 0x30: '8 hours', 0x48: '12 hours'},
     'PT-P910BT', ''),
    ('auto_power_off', 'Auto power off (AC adapter)', '1b6955410100', '1b6955410000', 32, 30,
     {0x00: 'Never', 0x06: '1 hour', 0x0C: '2 hours', 0x18: '4 hours', 0x30: '8 hours', 0x48: '12 hours'},
     'QL-1100 QL-1110NWB', ''),
    ('auto_power_off', 'Auto power off', '1b69554101', '1b69554100', 32, 30,
     {0x00: 'Never', 0x01: '10 minutes', 0x02: '20 minutes', 0x03: '30 minutes', 0x04: '40 minutes', 0x05: '50 minutes', 0x06: '1 hour'},
     'QL-600', ''),
    ('auto_power_off', 'Auto power off (AC adapter)', '1b69554101', '1b69554100', 32, 30,
     {0x00: 'Never', 0x01: '10 minutes', 0x02: '20 minutes', 0x03: '30 minutes', 0x04: '40 minutes', 0x05: '50 minutes', 0x06: '1 hour'},
     'QL-800', ''),
    ('auto_power_off', 'Auto power off (AC adapter)', '1b6955410100', '1b6955410000', 32, 30,
     {0x00: 'Never', 0x01: '10 minutes', 0x02: '20 minutes', 0x03: '30 minutes', 0x04: '40 minutes', 0x05: '50 minutes', 0x06: '1 hour'},
     'QL-810W QL-820NWB', ''),
    ('auto_power_off', 'Auto power off', '1b69554101', '1b69554100', 32, 30,
     {0x00: 'Never', 0x06: '1 hour', 0x0C: '2 hours', 0x18: '4 hours', 0x30: '8 hours', 0x48: '12 hours'},
     'TP-M5000N', ''),
    ('auto_power_off_battery', 'Auto power off (battery)', '1b6955410101', '1b6955410001', 3, 2,
     {0x00: 'Never', 0x01: '10 minutes', 0x02: '20 minutes', 0x03: '30 minutes', 0x04: '40 minutes', 0x05: '50 minutes', 0x06: '1 hour'},
     'PT-D800W PT-E800W PT-P900W PT-P910BT PT-P950NW', ''),
    ('auto_power_off_battery', 'Auto power off (battery)', '1b6955410100', '1b6955410000', 32, 30,
     {0x00: 'Never', 0x01: '10 minutes', 0x02: '20 minutes', 0x03: '30 minutes', 0x04: '40 minutes', 0x05: '50 minutes', 0x06: '1 hour'},
     'PT-P710BT PT-P715eBT', ''),
    ('auto_power_off_battery', 'Auto power off (battery)', '1b6955410101', '1b6955410001', 32, 30,
     {0x00: 'Never', 0x01: '10 minutes', 0x02: '20 minutes', 0x03: '30 minutes', 0x04: '40 minutes', 0x05: '50 minutes', 0x06: '1 hour'},
     'QL-810W QL-820NWB', ''),
    ('auto_power_on', 'Power on when plugged in', '1b69557001', '1b69557000', 32, 30,
     {0x00: 'Off', 0x01: 'On'},
     'PT-D800W PT-E800W PT-P710BT PT-P715eBT PT-P900W PT-P910BT PT-P950NW QL-1100 QL-1110NWB QL-600 QL-800 QL-810W QL-820NWB', ''),
    ('cut_mode', 'Cutter', '1b695863310000', '1b695863320100', 3, 2,
     {0x00: 'Off', 0x01: 'Cut after each label', 0x08: 'Cut at end of job'},
     'QL-1100 QL-1110NWB', ''),
    ('print_density_1', 'Print density (color 1)', '1b69586531000001', '1b69586532010001', 3, 2,
     {0xFA: '-6', 0xFB: '-5', 0xFC: '-4', 0xFD: '-3', 0xFE: '-2', 0xFF: '-1', 0x00: '0', 0x01: '+1', 0x02: '+2', 0x03: '+3', 0x04: '+4', 0x05: '+5', 0x06: '+6'},
     'QL-800 QL-810W QL-820NWB', ''),
    ('print_density_2', 'Print density (color 2)', '1b69586531000002', '1b69586532010002', 3, 2,
     {0xFA: '-6', 0xFB: '-5', 0xFC: '-4', 0xFD: '-3', 0xFE: '-2', 0xFF: '-1', 0x00: '0', 0x01: '+1', 0x02: '+2', 0x03: '+3', 0x04: '+4', 0x05: '+5', 0x06: '+6'},
     'QL-800 QL-810W QL-820NWB', ''),
    ('length_adjustment', 'Label length adjustment', '1b69582c31010020', '1b69582c32020020', 3, 2,
     {0x78: '-4', 0x7A: '-3', 0x7C: '-2', 0x7E: '-1', 0x80: '0', 0x82: '+1', 0x84: '+2', 0x86: '+3', 0x88: '+4'},
     'PT-D800W PT-E800W PT-P900W PT-P910BT PT-P950NW', ''),
    ('length_adjustment', 'Label length adjustment', '550b040d', '550b030d', 1, 0,
     {0x46: '-3%', 0x50: '-2%', 0x5A: '-1%', 0x64: '0%', 0x6E: '+1%', 0x78: '+2%', 0x82: '+3%'},
     'PT-P710BT PT-P715eBT', ''),
    ('full_cut_margin', 'Full cut margin adjustment', '1b69582c31010022', '1b69582c32020022', 3, 2,
     {0x72: '-2', 0x79: '-1', 0x80: '0', 0x87: '+1', 0x8E: '+2'},
     'PT-D800W PT-E800W PT-P900W PT-P910BT PT-P950NW', ''),
    ('half_cut_margin', 'Half cut margin adjustment', '1b69582c31010024', '1b69582c32020024', 3, 2,
     {0x72: '-2', 0x79: '-1', 0x80: '0', 0x87: '+1', 0x8E: '+2'},
     'PT-D800W PT-E800W PT-P900W PT-P910BT PT-P950NW', ''),
    ('print_position', 'Print position adjustment', '1b69556d01', '1b69556d00', 1, 0,
     {0x00: '-2', 0x01: '-1', 0x02: '0', 0x03: '+1', 0x04: '+2'},
     'TP-M5000N', ''),
    ('special_tape_feed', 'Special tape feed', '1b69115342000000', '1b69115342010100', 6, 5,
     {0x00: 'Off', 0x01: 'On'},
     'PT-P910BT', ''),
    ('battery_charge_limit', 'Battery charge limit', '1b69583d310300000000', '1b69583d3203000000', 3, 2,
     {0x00: '100%', 0x01: '80%'},
     'QL-810W QL-820NWB', ''),
    ('print_data_after_printing', 'Print data after printing', '1b695873310000', '1b695873320100', 3, 2,
     {0x01: 'Erase', 0x00: 'Keep'},
     'QL-1100 QL-1110NWB QL-800 QL-810W QL-820NWB', ''),
    ('print_data_after_printing', 'Print data after printing', '1b695873310100', '1b695873320100', 3, 2,
     {0x01: 'Erase', 0x00: 'Keep'},
     'QL-600', ''),
    ('info_report', 'Information report contents', '1b69586f310100', '1b69586f320100', 3, 2,
     {0x00: 'Transferred data', 0x01: 'Printer settings', 0x02: 'Usage log', 0x03: 'All'},
     'PT-D800W PT-E800W PT-P710BT PT-P715eBT PT-P900W PT-P910BT PT-P950NW', ''),
    ('info_report', 'Information report contents', '1b69586f310000', '1b69586f320100', 3, 2,
     {0x00: 'Transferred data', 0x01: 'Printer settings', 0x02: 'Usage log', 0x03: 'All'},
     'QL-1100 QL-1110NWB QL-810W QL-820NWB', ''),
    ('save_print_log', 'Save print log', '1b6958673102000000', '1b6958673203000000', 3, 2,
     {0x00: 'Off', 0x01: 'On'},
     'PT-D800W PT-E800W PT-P900W PT-P950NW', ''),
    ('serialize_mode', 'Numbering after a job', '1b69584f310000', '1b69584f320100', 3, 2,
     {0x01: 'Continue from last number', 0x00: 'Reset to starting number'},
     'QL-1100 QL-1110NWB', ''),
    ('command_mode', 'Command mode', '1b69556101', '1b69556100', 32, 30,
     {0x01: 'Raster', 0x00: 'ESC/P', 0x03: 'P-touch Template'},
     'QL-1100 QL-1110NWB QL-810W QL-820NWB', 'The mode the printer starts in.'),
]

# model: (print the settings report, restore factory settings); None where the
# tool offers no such button for the model
_ACTIONS = {
    'PT-D800W': ('1b69554e', '1b695569'),
    'PT-E800W': ('1b69554e', '1b695569'),
    'PT-P710BT': ('1b69554e', '1b695558'),
    'PT-P715eBT': ('1b69554e', '1b695558'),
    'PT-P900W': ('1b69554e', '1b695569'),
    'PT-P910BT': ('1b69554e', '1b695569'),
    'PT-P950NW': ('1b69554e', '1b695569'),
    'QL-1100': ('1b69554e', '1b69555a'),
    'QL-1110NWB': ('1b69554e', '1b69555a'),
    'QL-600': (None, '1b695569'),
    'QL-800': (None, '1b695569'),
    'QL-810W': ('1b69554e', '1b69555a'),
    'QL-820NWB': ('1b69554e', '1b69555a'),
    'TP-M5000N': (None, '1b695569'),
}


def _build():
    models = {}
    for name, (report, reset) in _ACTIONS.items():
        settings = tuple(
            Setting(key, label, bytes.fromhex(get), bytes.fromhex(set_), size, index,
                    choices, note)
            for key, label, get, set_, size, index, choices, names, note in _ROWS
            if name in names.split())
        models[name] = Model(name, settings,
                             report and bytes.fromhex(report),
                             reset and bytes.fromhex(reset))
    return models


MODELS = _build()
