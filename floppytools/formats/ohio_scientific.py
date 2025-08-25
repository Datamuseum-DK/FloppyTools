#!/usr/bin/env python3

'''
   Ohio Scientific '65U' format
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

from ..base import media

class OhioScientific(media.Media):

    ''' Ohio Scientific '''

    SECTOR_SIZE = 0xf << 8
    GEOMETRY = ((0, 0, 0), (76, 0, 0), SECTOR_SIZE)

    def process_stream(self, stream):
        retval = False

        flux = stream.fm_flux()

        b = []
        i = flux.find('|')
        while i + 4 < len(flux):
            if flux[i:i+4] == '|---':
                b.append(1)
                i += 4
            elif flux[i:i+4] == '|-|-':
                b.append(0)
                i += 4
            else:
                b.append(None)
                i = flux.find('|', i + 1)

        data = []
        state = 0
        bi = 0
        prev = 0
        while bi + 10 < len(b):

            if b[bi] != 0:
                try:
                    j = b.index(0, bi)
                except ValueError:
                    break
                #print("_%d" % (j-bi))
                bi = j
                continue

            sw = b[bi+0:bi+11]

            if None in sw:
                j = sw.index(None) + 1
                #print(b[bi:bi+j])
                bi += j
                #print("_CK", sw)
                state = 0
                data = []
                continue

            prev = bi
            nw = ''.join(str(x) for x in b[bi+10:bi+15])
            o = 0
            for n, m in enumerate(sw[1:9]):
                if m:
                    o |= 1<<n

            if state < 5:

                bi += 11
                if sw[10] != 1:
                    #print("_FE", sw)
                    state = 0
                    data = []
                    continue

                if (sw.count(1) & 1) == 0:
                    #print("_PE", sw)
                    state = 0
                    data = []
                    continue
            else:

                bi += 10
                if sw[9] != 1:
                    #print("_fe", sw)
                    state = 0
                    data = []
                    continue

            data.append(o)

            if state == 0 and o != 0x80:
                state = 1
            elif state == 0:
                state = 2
            elif state == 2:
                state = 3
            elif state == 3:
                bi += 25
                #self.trace(''.join(str(x) for x in b[bi:bi+40]))
                state = 5
            elif state == 5:
                state = 5

            if 0x20 <= o <= 0x7e:
                c = "%c" % o
            else:
                c = " "

            if False:
                self.trace(
                    state,
                    "%08x" % (bi-prev),
                    ''.join(str(x) for x in sw),
                    "%02x" % o,
                    c,
                    "0x%04x" % len(data),
                    nw,
                    hex(sum(data))
                )
            if state == 5 and len(data) > 10 and len(data) != 0xe06:
                csum = sum(data[:-2]) & 0xffff
                dsum = (data[-2] << 8) | data[-1]
                if csum == dsum:
                    self.trace(
                        "_CSUM*",
                        "%04x" % csum,
                        "%04x" % dsum,
                        hex(len(data)),
                        bytes(data).hex()
                    )

            if state == 5 and len(data) == 3590:
                csum = sum(data[:-2]) & 0xffff
                dsum = (data[-2] << 8) | data[-1]
                if csum == dsum:
                    self.trace(
                        "_CSUM",
                        "%04x" % csum,
                        "%04x" % dsum,
                        csum == dsum,
                        bytes(data[:10]).hex()
                    )
                    if len(data) < 0xf00:
                        data += bytes(0 for x in range(0xf00 - len(data)))
                    self.did_read_sector(
                        stream,
                        bi,
                        (data[2], 0, 0),
                        bytes(data),
                    )
                    retval = True
                else:
                    self.trace(
                        "_CSUM",
                        "%04x" % csum,
                        "%04x" % dsum,
                        csum == dsum,
                        bytes(data).hex()
                    )
                state = 0
                data = []
            if state == 1 and len(data) > 0x100 and len(data) == data[2]<<8:
                csum = sum(data[:-2]) & 0xffff
                dsum = (data[-2] << 8) | data[-1]
                self.trace(
                    "_FIN",
                    "%04x" % csum,
                    "%04x" % dsum,
                    csum == dsum,
                    bytes(data[:10]).hex()
                )
                if len(data) < 0xf00:
                    data += bytes(0 for x in range(0xf00 - len(data)))
                self.did_read_sector(
                    stream,
                    bi,
                    (0, 0, 0),
                    bytes(data),
                    flags=["boot"]
                )
                retval = True
                state = 0
                data = []

        return retval

ALL = [
    OhioScientific,
]
