# FloppyTools

Some python tools we use for preservation of rare floppy disks in
Datamuseum.dk

There are many other and good tools for reading floppy disks,
FluxEngine, HXC and so on, so why another one ?

We have some uncommon floppies in our collection, and more often
than not, have to reverse-engineer the format ourselves, so
FloppyTools is written in python and structured to make experiments
and hacking easier.

One particular focus is being able to manually salvage individual
sectors, using whatever heuristics are deemed justified by the
person behind the keyboard.

We have made an example of this available in:

https://github.com/Datamuseum-DK/FloppyToolsExamples

FloppyTools will at all times be a work-in-progress, but I hope
somebody will find it useful, and I would be very happy to see
support for the weird formats migrate from FloppyTools to other
packages, where they will run faster.

Formats currently supported:

* DEC RX02 (dec_rx02.py, uses special M²FM encoding)

* Data General Nova (dg_nova.py, uses the worlds second worst CRC-16)

* HP9885 (hp98xx.py, almost, but not quite like IBM format)

* IBM (ibm.py, mostly to be able to fix individual sectors)

* Intel ISIS-II (intel_isis.py, M²FM encoding)

* Q1 MicroLite (q1_microlite.py, per-track non 2^N sector lengths)

* WANG WCS (wang_wcs.py, very old text-processing)

* Zilog MCZ/1 (zilog_mcz.py, sectors form doubly-linked lists)

/phk
