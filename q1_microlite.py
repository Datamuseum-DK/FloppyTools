#/usr/bin/env python3

'''
   Q1 Microlite floppies
   ~~~~~~~~~~~~~~~~~~~~~

'''

import main
import disk
import fluxstream

class CR(fluxstream.ClockRecovery):

    SPEC = {
        77: "-|",
        115: "--|",
        154: "---|",
        192: "----|",
        231: "-----|",
    }

def totext(data):
    txt = []
    for i in data:
        if 32 < i <= 126:
            txt.append("%c" % i)
        elif i == 32:
            txt.append("…")
        else:
            txt.append(" ")
    return "".join(txt)

class Q1MicroLite(disk.DiskFormat):

    GAP = '|-' * 16 + '---|-'
    DATA_PATTERN = GAP + fluxstream.make_mark(0x20, 0x9b)
    AM_PATTERN = GAP + fluxstream.make_mark(0x20, 0x9e)

    def define_geometry(self, media):
        ''' Possibly not precise wrt. cylinder ranges '''
        media.define_geometry((0, 0, 0), (0, 0, 87), 40)
        media.define_geometry((1, 0, 0), (29, 0, 18), 255)
        media.define_geometry((30, 0, 0), (72, 0, 125), 20)
        media.define_geometry((73, 0, 0), (73, 0, 18), 255)
        media.define_geometry((74, 0, 0), (76, 0, 18), 512)

    def process(self, stream):

        flux = CR().process(stream.iter_dt())

        for am_pos in stream.iter_pattern(flux, pattern=self.AM_PATTERN):

            am_data = stream.flux_data_mfm(flux[am_pos:am_pos+48])
            if (am_data[0] + am_data[1]) & 0xff != am_data[2]:
                continue

            data_pos = flux.find(
                self.DATA_PATTERN,
                am_pos+100,
                am_pos+150 + len(self.DATA_PATTERN)
            )
            if data_pos < 0:
                continue
            data_pos += len(self.DATA_PATTERN)

            if am_data[0] == 0:
                length = 40
            elif am_data[0] < 30:
                length = 255
            elif am_data[0] < 73:
                length = 20
            elif am_data[0] < 74:
                length = 255
            else:
                length = 1024

            data = stream.flux_data_mfm(flux[data_pos-16:data_pos+16*length+32])
            assert data[0] == 0x9b

            dsum = sum(data[:-2]) & 0xff
            if dsum == data[-2] and data[-1] == 0x10:
                yield disk.Sector(
                    (am_data[0], 0, am_data[1]),
                    data,
                )
            elif 0:
                print(
                    am_data.hex(),
                    "CSUM",
                    "%02x" % dsum,
                    "%02x" % data[-1],
                    flux[data_pos-16:data_pos+16*length+64],
                    #totext(data),
                    #data.hex(),
                )

if __name__ == "__main__":
    main.Main(Q1MicroLite)
