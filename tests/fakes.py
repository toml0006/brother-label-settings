"""A stand-in printer: holds one byte per setting, answers gets, applies sets."""
from brother_label_settings import protocol


class FakePrinter:
    def __init__(self, model, **values):
        self.model = model
        self.values = {s.key: next(iter(s.choices)) for s in model.settings}
        self.values.update(values)
        self.writes = []
        self.pending = b""
        self.silent = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def model_name(self):
        return self.model.name

    def write(self, data):
        self.writes.append(bytes(data))
        for s in self.model.settings:
            if data == s.get and not self.silent:
                reply = bytearray(s.reply_size)
                if s.reply_size == 32:
                    reply[:2] = protocol.STATUS_HEADER
                reply[s.index] = self.values[s.key]
                self.pending += bytes(reply)
            elif data[:-1] == s.set:
                self.values[s.key] = data[-1]

    def read(self, size, timeout=None):
        out, self.pending = self.pending[:size], self.pending[size:]
        return out
