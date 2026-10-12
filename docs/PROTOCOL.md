# The settings protocol

What Brother's Printer Setting Tool (1.3.5 for macOS) sends to read and write a
printer's stored settings, as far as this project uses it. The bytes of a real
exchange below are from a QL-1100 over USB; nothing else has been observed on
hardware.

## Where it comes from

The tool has one definition per printer model. A definition lists the tool's
tabs; each tab has four wrapper commands and a list of settings; each setting
has a "get" command with a reply size and the position of the value in the
reply, a "set" command with a placeholder for the value, and the values the
setting can take. The tool's own program shows the order: the tab's "pre"
command, then one command per setting, then the tab's "post" command, each as a
separate USB write, with a read of the reply size after each "get" (it waits up
to half a second).

## The exchange

Reading:

```
1B 40  1B 69 61 01          ESC @ (initialise), ESC i a 01 (raster command mode)
<get>                       one per setting; read the reply after each
1B 69 61 FF
```

Writing:

```
1B 40  1B 69 61 01
<set> <value>               one per setting; no reply
1B 7E 53  1B 69 61 FF       ESC ~ S comes only after writes
```

The settings report and the factory reset are single writes: the preamble, the
command, `1B 69 61 FF`.

The wrapper commands are the same for every QL, PT and TP model in the tool.
The PJ models use `1B 69 61 00` in the preamble and are not covered here.

## Two families of command

`ESC i U <code> 01 [..]` reads and `ESC i U <code> 00 [..] <value>` writes.
On the QL-1100 the reply is 32 bytes and the value is byte 30:

```
> 1B 69 55 61 01                                 command mode, get
< 80 20 42 34 43 30 00 00 00 00 66 0B 00 00 2E 00
  00 99 F0 00 00 00 00 00 00 00 00 00 00 00 03 01
                                              ^^ 0x03 = P-touch Template
```

The reply is the printer's ordinary 32-byte status packet (`80 20 42` header,
media width `66` = 102 mm, media type `0B` = die-cut, and so on) with the
setting's value in a byte the status packet otherwise leaves unused. This
project rejects a 32-byte reply that does not start `80 20`.

`ESC i X <code> 31 ..` reads and `ESC i X <code> 32 .. <value>` writes. On the
QL-1100 the reply is 3 bytes, which look like a little-endian length followed
by the value:

```
> 1B 69 58 63 31 00 00                           cutter, get
< 01 00 01
        ^^ 0x01 = cut after each label
```

According to the definitions, some PT models answer an `ESC i U` command with 3
bytes instead of 32, and a few settings use other commands altogether. The
per-model tables in
`brother_label_settings/models.py` carry the reply size and value position for
each.

## Auto power off values

The value is a count of 10-minute units on most models: `06` is one hour and
`48` (72) is twelve. `00` is never. The PT-D800W family numbers its choices
`00` to `0A` instead, so `07` there is two hours, not seventy minutes. This is
why the tables list values per model and the tool refuses anything unlisted.

## Things that go wrong

**Stale replies.** If a program asks the printer for something and closes the
device before reading the answer, the answer is delivered to the next program
that reads. One unread 32-byte status packet shifts every reply after it: this
was seen on the QL-1100, where a 3-byte read then returned `80 20 42` and the
setting showed as `0x42`. Before the first "get" and before each one after it,
this project reads and discards whatever is pending.

**Empty reads.** With the Linux `usblp` driver, `select()` reports the device
readable when a read then returns zero bytes. In one measurement a reply took
about 150 ms to arrive. A read loop has to keep going until its deadline, not until the first
empty read, and must not treat "readable" as "data".

**One opener.** `usblp` lets one process open the device at a time; a second
gets `EBUSY`.

**Printing.** The preamble resets the printer's command state. Do not send any
of this while a job is printing.

## The model name

`usblp` returns the printer's IEEE 1284 device ID through the
`LPIOC_GET_DEVICE_ID` ioctl: two length bytes, then `KEY:value;` pairs. The
`MDL` field is the model (`QL-1100`), which is how the tool picks a table.
