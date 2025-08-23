#!/usr/bin/env python3

''' MACHINE GENERATED FILE, see make_index.py'''

documentation = {
    "DataGeneralNova": [
        ['Data General Nova 8" floppy disks'],
    ],
    "DecRx02": [
        ['IBM format 8" floppy disks'],
    ],
    "HP9885": [
        ['HP9885 8" floppies for MX21'],
    ],
    "Ibm": [
        ['IBM format floppy disks'],
    ],
    "IntelIsis": [
        ['Intel ISIS format 8" floppy disks'],
    ],
    "OhioScientific": [
        ['Ohio Scientific'],
    ],
    "Q1MicroLiteFM": [
        ['Q1 Corporation MicroLite FM format floppy disks\n\n\tBla\n\n\tFOo'],
    ],
    "Q1MicroLiteMFM28": [
        ['Q1 Corporation MicroLite MFM format floppy disks'],
    ],
    "Q1MicroLiteMFM39": [
        ['Q1 Corporation MicroLite MFM format floppy disks'],
    ],
    "WangWcs": [
        ['WANG WCS format 8" floppy disks'],
    ],
    "ZilogMCZ": [
        ['...'],
    ],
}

aliases = {
    "IBM": [
        "Ibm",
    ],
    "Q1": [
        "Q1MicroLiteMFM28",
        "Q1MicroLiteMFM39",
        "Q1MicroLiteFM",
    ],
}

def find_formats(target):
    if target == "DataGeneralNova":
        from . import dg_nova
        yield ("DataGeneralNova", dg_nova.ALL[0])
    elif target == "DecRx02":
        from . import dec_rx02
        yield ("DecRx02", dec_rx02.ALL[0])
    elif target == "HP9885":
        from . import hp98xx
        yield ("HP9885", hp98xx.ALL[0])
    elif target == "IBM":
        from . import ibm
        yield ("Ibm", ibm.ALL[0])
    elif target == "Ibm":
        from . import ibm
        yield ("Ibm", ibm.ALL[0])
    elif target == "IntelIsis":
        from . import intel_isis
        yield ("IntelIsis", intel_isis.ALL[0])
    elif target == "OhioScientific":
        from . import ohio_scientific
        yield ("OhioScientific", ohio_scientific.ALL[0])
    elif target == "Q1":
        from . import q1_microlite
        yield ("Q1MicroLiteMFM28", q1_microlite.ALL[0])
        yield ("Q1MicroLiteMFM39", q1_microlite.ALL[1])
        yield ("Q1MicroLiteFM", q1_microlite.ALL[2])
    elif target == "Q1MicroLiteFM":
        from . import q1_microlite
        yield ("Q1MicroLiteFM", q1_microlite.ALL[2])
    elif target == "Q1MicroLiteMFM28":
        from . import q1_microlite
        yield ("Q1MicroLiteMFM28", q1_microlite.ALL[0])
    elif target == "Q1MicroLiteMFM39":
        from . import q1_microlite
        yield ("Q1MicroLiteMFM39", q1_microlite.ALL[1])
    elif target == "WangWcs":
        from . import wang_wcs
        yield ("WangWcs", wang_wcs.ALL[0])
    elif target == "ZilogMCZ":
        from . import zilog_mcz
        yield ("ZilogMCZ", zilog_mcz.ALL[0])
    elif target == "all":
        from . import dec_rx02
        yield ("DecRx02", dec_rx02.ALL[0])
        from . import dg_nova
        yield ("DataGeneralNova", dg_nova.ALL[0])
        from . import hp98xx
        yield ("HP9885", hp98xx.ALL[0])
        from . import ibm
        yield ("Ibm", ibm.ALL[0])
        from . import intel_isis
        yield ("IntelIsis", intel_isis.ALL[0])
        from . import ohio_scientific
        yield ("OhioScientific", ohio_scientific.ALL[0])
        from . import q1_microlite
        yield ("Q1MicroLiteMFM28", q1_microlite.ALL[0])
        yield ("Q1MicroLiteMFM39", q1_microlite.ALL[1])
        yield ("Q1MicroLiteFM", q1_microlite.ALL[2])
        from . import wang_wcs
        yield ("WangWcs", wang_wcs.ALL[0])
        from . import zilog_mcz
        yield ("ZilogMCZ", zilog_mcz.ALL[0])
