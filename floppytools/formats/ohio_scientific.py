#!/usr/bin/env python3

'''
   Ohio Scientific 'OS65U' format
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

from ..base import media

class RxErr(Exception):
    ''' ... '''

class OhioScientificU(media.Media):

    ''' Ohio Scientific OS65U format '''

    SECTOR_SIZE = 0xf << 8
    GEOMETRY = ((0, 0, 0), (76, 0, 0), SECTOR_SIZE)

    def process_stream(self, stream):
        self.retval = False

        flux = stream.fm_flux()

        def fm():
            ''' One FM coded bit '''
            n = 0
            while n < len(flux):
                cell = flux[n:n+4]
                if cell == '|---':
                    yield 1
                    n += 4
                elif cell == '|-|-':
                    yield 0
                    n += 4
                else:
                    n += 1

        fmi = fm()

        def element(nbit):
            ''' One async element (byte+parity+stopbit) '''
            g = 0
            while next(fmi):
                g += 1
                continue
            c = 0
            for i in range(nbit):
                c += next(fmi) << i
            return g, c

        def rx8e():
            ''' 8 bits with even parity '''
            gap, bits = element(10)
            if bits == 0:
                raise RxErr("Break")
            if not bits & 0x200:
                raise RxErr("Stop-Bit")
            par = bin(bits).count('1')
            if not par & 1:
                raise RxErr("Parity")
            return gap, bits & 0xff

        def rx8n():
            ''' 8 bits with no parity '''
            gap, bits = element(9)
            if bits == 0:
                raise RxErr("Break")
            if not bits & 0x100:
                raise RxErr("Stop-Bit")
            return gap, bits & 0xff

        def got(l):
            ''' we think we got a sector (=track) '''
            if len(l) > 3000:
                b = bytes(l)
                if stream.chs[0] == 0:
                    w = b[2] << 8
                    if len(b) >= w:
                        self.did_read_sector(
                            stream,
                            0,
                            (0, 0, 0),
                            b[:w] + bytes(0 for i in range(0xf00 - w)),
                        )
                        self.retval = True
                    check = None
                elif len(b) >= 3590:
                    cs = sum(b[:3588]) & 0xffff
                    rs = (b[3588] << 8) | b[3589]
                    check = cs == rs
                    if check:
                        self.did_read_sector(
                            stream,
                            1,
                            (b[2], 0, 0),
                            b[:3590] + bytes(0 for i in range(0xf00 - 3590)),
                        )
                        self.retval = True
                    elif check is False:
                        check = hex(cs)
                else:
                    check = None
                self.trace("GOT", len(l), check, stream.chs, b[:3].hex(), hex(b[4]), b[3588:].hex())
            return []

        l = []
        while True:
            try:
                if stream.chs[0] == 0 or len(l) < 3:
                    gap, val = rx8e()
                else:
                    gap, val = rx8n()
                if stream.chs[0] > 0 and len(l) == 3 and gap:
                    if len(l) == 3 and gap < 30 and val >= 0xf0:
                        # Ignore transient from UART being switched from 8E to 8N
                        self.trace("gap", gap, hex(val), len(l))
                        continue
                    self.trace("GAP", gap, hex(val), len(l))
            except RxErr:
                l = got(l)
                continue
            except StopIteration:
                l = got(l)
                break
            if gap > 400:
                l = got(l)
            l.append(val)

        return self.retval

ALL = [
    OhioScientificU,
]
