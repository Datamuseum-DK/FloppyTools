#/usr/bin/env python3

'''
   Commodore 4040/1541 floppy disks
   ================================
'''

from ..base import media

GCR = {
    0x0a: 0x0,
    0x0b: 0x1,
    0x12: 0x2,
    0x13: 0x3,
    0x0e: 0x4,
    0x0f: 0x5,
    0x16: 0x6,
    0x17: 0x7,
    0x09: 0x8,
    0x19: 0x9,
    0x1a: 0xa,
    0x1b: 0xb,
    0x0d: 0xc,
    0x1d: 0xd,
    0x1e: 0xe,
    0x15: 0xf,
}

class CBM64(media.Media):
    ''' Commodore 4040/1541 floppy disks '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.define_geometry((1, 0, 0), (17, 0, 20), 256)
        self.define_geometry((18, 0, 0), (24, 0, 18), 256)
        self.define_geometry((25, 0, 0), (30, 0, 17), 256)
        self.define_geometry((31, 0, 0), (35, 0, 16), 256)
        self.x = 0
        self.dx = 0
        self.clock = 64

    def process_stream(self, stream):

        retval = False

        if stream.chs[1] & 1:
            # I wonder if we can decode the B side of "flip" disks backwards on the odd tracks ?
            return retval

        self.x = 0
        self.dx = 0
        self.clock = 64

        def bit_slicer():
            ''' Estimate clock frequency and decode bits '''

            for dt in stream.iter_dt():
                self.x += dt
                if dt < 96:
                    self.clock += (dt - self.clock) / 200
                w = dt / self.clock
                if w < 1.5:
                    yield 1
                elif w < 2.5:
                    yield 0
                    yield 1
                else:
                    yield 0
                    yield 0
                    yield 1

        def nibble_slicer():
            ''' Locate sync and decode GCR nibbles '''

            bsl_iter = bit_slicer()
            while True:
                acc = [0] * 20
                while True:
                    try:
                        b = next(bsl_iter)
                    except StopIteration:
                        yield -1
                        return
                    w = acc[-5] << 4
                    w += acc[-4] << 3
                    w += acc[-3] << 2
                    w += acc[-2] << 1
                    w += acc[-1] << 0
                    if 0 not in acc and not b:
                        self.dx = self.x
                        break
                    acc.append(b)
                    acc.pop(0)
                while True:
                    h = b << 4
                    try:
                        h += next(bsl_iter) << 3
                        h += next(bsl_iter) << 2
                        h += next(bsl_iter) << 1
                        h += next(bsl_iter) << 0
                    except StopIteration:
                        yield -1
                        return
                    hh = GCR.get(h, -1)
                    yield hh
                    if hh < 0:
                        break
                    try:
                        b = next(bsl_iter)
                    except StopIteration:
                        yield -1
                        return

        def data_slicer():
            ''' Decode octets and check checksums '''

            nsl_iter = nibble_slicer()
            run = True
            while run:
                csum = 0
                octets = []
                fail = False
                while True:
                    try:
                        h = next(nsl_iter)
                        if h < 0:
                            break
                        l = next(nsl_iter)
                        if l < 0:
                            break
                        if fail:
                            continue
                        o = (h << 4) | l
                        octets.append(o)
                        if len(octets) > 1:
                            csum ^= o
                        if octets[0] == 8 and len(octets) == 6:
                            if csum == 0:
                                yield bytes(octets)
                            else:
                                self.trace("BAD SUM", "%02x" % csum, bytes(octets).hex())
                                fail = True
                        elif octets[0] == 7 and len(octets) == 258:
                            if csum == 0:
                                yield bytes(octets)
                            else:
                                self.trace("BAD SUM", "%02x" % csum, bytes(octets).hex())
                                fail = True
                        elif octets[0] not in (7, 8):
                            self.trace("BAD DATA", bytes(octets).hex())
                            fail = True
                    except StopIteration:
                        run = False
                        break

        amx = -1
        am = b''
        for r in data_slicer():
            if r[0] == 8:
                am = r
                amx = self.dx
            elif r[0] == 7 and amx > 0 and 9000 < self.dx - amx < 20000:
                self.trace(
                    "%8d" % amx,
                    "%8d" % self.dx,
                    "%8d" % (self.dx - amx),
                    stream.chs,
                    am.hex(),
                    r.hex()
                )
                am_chs = (am[3],0, am[2])
                self.did_read_sector(
                    stream,
                    amx,
                    am_chs,
                    r[2:],
                    (am[4:6].hex()),
                )
                retval = True
                am = b''
                amx = 0
            elif r[0] == 7 and amx < 0:
                pass
            elif r[0] == 7 and amx == 0:
                self.trace("BAD NO_AM", self.clock, len(r), amx, self.dx, self.dx - amx)
            elif r[0] == 7:
                self.trace("BAD AM_DISTANCE", self.clock, len(r), amx, self.dx, self.dx - amx)
                am = b''
                amx = 0

        return retval

ALL = [
    CBM64,
]
