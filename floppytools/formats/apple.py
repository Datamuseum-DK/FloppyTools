#/usr/bin/env python3

'''
   Apple ][ DOS 3.3 floppies 
   =========================
'''

from ..base import media

GCR5 = {
    0xab: 0x00, 0xad: 0x01, 0xae: 0x02, 0xaf: 0x03,
    0xb5: 0x04, 0xb6: 0x05, 0xb7: 0x06, 0xba: 0x07,
    0xbb: 0x08, 0xbd: 0x09, 0xbe: 0x0a, 0xbf: 0x0b,
    0xd6: 0x0c, 0xd7: 0x0d, 0xda: 0x0e, 0xdb: 0x0f,
    0xdd: 0x10, 0xde: 0x11, 0xdf: 0x12, 0xea: 0x13,
    0xeb: 0x14, 0xed: 0x15, 0xee: 0x16, 0xef: 0x17,
    0xf5: 0x18, 0xf6: 0x19, 0xf7: 0x1a, 0xfa: 0x1b,
    0xfb: 0x1c, 0xfd: 0x1d, 0xfe: 0x1e, 0xff: 0x1f,
}

GCR6 = {
    0x96: 0x00, 0x97: 0x01, 0x9A: 0x02, 0x9B: 0x03,
    0x9D: 0x04, 0x9E: 0x05, 0x9F: 0x06, 0xA6: 0x07,
    0xA7: 0x08, 0xAB: 0x09, 0xAC: 0x0A, 0xAD: 0x0B,
    0xAE: 0x0C, 0xAF: 0x0D, 0xB2: 0x0E, 0xB3: 0x0F,
    0xB4: 0x10, 0xB5: 0x11, 0xB6: 0x12, 0xB7: 0x13,
    0xB9: 0x14, 0xBA: 0x15, 0xBB: 0x16, 0xBC: 0x17,
    0xBD: 0x18, 0xBE: 0x19, 0xBF: 0x1A, 0xCB: 0x1B,
    0xCD: 0x1C, 0xCE: 0x1D, 0xCF: 0x1E, 0xD3: 0x1F,
    0xD6: 0x20, 0xD7: 0x21, 0xD9: 0x22, 0xDA: 0x23,
    0xDB: 0x24, 0xDC: 0x25, 0xDD: 0x26, 0xDE: 0x27,
    0xDF: 0x28, 0xE5: 0x29, 0xE6: 0x2A, 0xE7: 0x2B,
    0xE9: 0x2C, 0xEA: 0x2D, 0xEB: 0x2E, 0xEC: 0x2F,
    0xED: 0x30, 0xEE: 0x31, 0xEF: 0x32, 0xF2: 0x33,
    0xF3: 0x34, 0xF4: 0x35, 0xF5: 0x36, 0xF6: 0x37,
    0xF7: 0x38, 0xF9: 0x39, 0xFA: 0x3A, 0xFB: 0x3B,
    0xFC: 0x3C, 0xFD: 0x3D, 0xFE: 0x3E, 0xFF: 0x3F,
}

class AppleII(media.Media):
    ''' Apple ][ floppy disks '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.define_geometry((0, 0, 0), (34, 0, 15), 256)
        self.x = 0
        self.clock = 80

    def process_stream(self, stream):

        retval = False

        if stream.chs[1] & 1:
            # I wonder if we can decode the B side of "flip" disks backwards on the odd tracks ?
            return retval

        self.x = 0
        self.clock = 80
        amx = 0
        am = b'\xff\xff\xff\xff'

        def bit_slicer():
            ''' Estimate clock frequency and decode bits '''

            for dt in stream.iter_dt():
                self.x += dt
                if dt < 120:
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

        def gw(n):
            ''' Get a word of N bits '''
            x = 0
            for _i in range(n):
                x <<= 1
                x |= next(bsl_iter)
            while n == 8 and not x & 0x80:
                x <<= 1
                x |= next(bsl_iter)
            return x

        def g44():
            ''' Get a byte encoded in interleaved FM format '''
            x = 0
            y = [7, 5, 3, 1, 6, 4, 2, 0]
            for i in range(8):
                if not next(bsl_iter):
                    return -1
                x |= next(bsl_iter) << y[i]
            return x

        try:
            bsl_iter = bit_slicer()
            sync = 0xff << 2
            acc = 0
            while True:
                while True:
                    acc <<= 1
                    acc |= next(bsl_iter)
                    acc &= 0x3ff
                    if acc == sync:
                        break

                while acc == sync:
                    acc = gw(10)

                if acc == 0x3ff:
                    # Address mark

                    acc &= 0x3
                    acc <<= 22
                    acc |= gw(22)
                    if acc != 0xd5aa96:
                        self.trace("D %06x" % acc)
                        continue

                    hdr = list(g44() for i in range(4))
                    if -1 in hdr:
                        self.trace("E ", hdr)
                        continue

                    am = bytes(hdr)
                    if am[0] ^ am[1] ^ am[2] ^ am[3]:
                        self.trace("F ", am.hex(), hex(am[0] ^ am[1] ^ am[2] ^ am[3]))
                        continue

                    acc = gw(19) << 5
                    if acc != 0xdeaae0:
                        self.trace("G", am.hex(), "%06x" % acc)
                        continue

                    self.trace("AM", am.hex())
                    amx = self.x

                elif acc == 0x3fd:
                    # Sector data

                    dx = self.x
                    if amx == 0 or not 0x1500 < dx - amx < 0x1700:
                        self.trace("BAD MISSING AM", hex(dx), hex(amx), hex(dx - amx))
                        continue

                    acc &= 0x1
                    acc <<= 23
                    acc |= gw(23)
                    if acc != 0xd5aaad:
                        self.trace("BAD SECTOR HEAD", am.hex(), "%06x" % acc)
                        continue

                    d6 = []
                    for _i in range(343):
                        d6.append(GCR6.get(gw(8), -1))

                    if -1 in d6:
                        self.trace("BAD GCR DECODE", am.hex(), d6)
                        continue

                    # 2 bytes to catch surplus bits
                    data = [0] * 258
                    csum = 0

                    # 0x56 = round_up(256/3)
                    for i, b in enumerate(d6[:0x56]):
                        csum ^= b
                        data[i + 0x00] |= ((csum >> 1) & 1) | ((csum << 1) & 2)
                        data[i + 0x56] |= ((csum >> 3) & 1) | ((csum >> 1) & 2)
                        data[i + 0xac] |= ((csum >> 5) & 1) | ((csum >> 3) & 2)

                    for i, b in enumerate(d6[0x56:]):
                        csum ^= b
                        data[i] |= (csum << 2)

                    if csum:
                        self.trace("BAD CHECKUM", am.hex(), "%02x" % csum)
                        continue

                    tail = gw(24)
                    if tail != 0xdeaaeb:
                        self.trace("BAD TAIL", am.hex(), "%06x" % tail)
                        continue

                    self.trace(
                        "GOOD READ",
                        am.hex(),
                        hex(dx - amx),
                        "%04x" % sum(data),
                        "CS %02x" % csum,
                        data[256:],
                        "%06x" % tail,
                    )
                    self.did_read_sector(
                        stream,
                        amx,
                        (am[1], 0, am[2]),
                        bytes(data[:256]),
                    )
                    retval = True

        except StopIteration:
            pass

        return retval

ALL = [
    AppleII,
]
