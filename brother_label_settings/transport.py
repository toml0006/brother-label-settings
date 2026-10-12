"""The printer on Linux, through the kernel's usblp character device."""
import errno
import fcntl
import os
import select
import time

DEFAULT_DEVICE = os.environ.get("USB_DEVICE", "/dev/usb/lp0")

# LPIOC_GET_DEVICE_ID with a 1024-byte buffer: _IOC(_IOC_READ, 'P', 1, 1024)
_GET_DEVICE_ID = 0x84005001


class UsbLp:
    def __init__(self, path=DEFAULT_DEVICE, busy_wait=3.0):
        # usblp admits one opener at a time; anything else polling the printer
        # (a status page, say) holds it for a moment
        deadline = time.monotonic() + busy_wait
        while True:
            try:
                self.fd = os.open(path, os.O_RDWR)
                return
            except OSError as e:
                if e.errno != errno.EBUSY or time.monotonic() >= deadline:
                    raise
                time.sleep(0.1)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        os.close(self.fd)

    def write(self, data):
        while data:
            data = data[os.write(self.fd, data):]

    def read(self, size, timeout=1.0):
        """Up to `size` bytes; fewer if the printer goes quiet."""
        buf = b""
        deadline = time.monotonic() + timeout
        while len(buf) < size:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            if select.select([self.fd], [], [], min(left, 0.05))[0]:
                buf += os.read(self.fd, size - len(buf))
        return buf

    def model_name(self):
        """The model from the printer's IEEE 1284 device ID, e.g. "QL-1100"."""
        buf = bytearray(1024)
        fcntl.ioctl(self.fd, _GET_DEVICE_ID, buf)
        return parse_device_id(bytes(buf))


def parse_device_id(raw):
    """The MDL field of a device ID: two length bytes, then "KEY:value;" pairs."""
    text = raw[2:int.from_bytes(raw[:2], "big")].decode("ascii", "replace")
    fields = dict(f.split(":", 1) for f in text.split(";") if ":" in f)
    return (fields.get("MDL") or fields.get("MODEL") or "").strip() or None
