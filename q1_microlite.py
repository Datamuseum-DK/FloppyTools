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
        media.define_geometry((0, 0, 0), (29, 0, 18), 256)
        media.define_geometry((30, 0, 0), (71, 0, 125), 21)
        media.define_geometry((72, 0, 0), (79, 0, 18), 256)

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

            data = stream.flux_data_mfm(flux[data_pos-16:data_pos+16*21])
            assert data[0] == 0x9b

            if data[1] == 00:
                yield disk.Sector(
                    (am_data[0], 0, am_data[1]),
                    data,
                )
                print(
                    am_data.hex(),
                    "X %02x" % data[1],
                    data.hex(),
                    None,
                )
            elif 1 <= data[1] <= 7:
                dsum = sum(data[:-1]) & 0xff
                if dsum == data[-1]:
                    yield disk.Sector(
                        (am_data[0], 0, am_data[1]),
                        data,
                    )
                else:
                    print(
                        am_data.hex(),
                        "Y %02x" % data[1],
                        data[:21].hex(),
                        totext(data),
                        dsum == data[-1],
                    )
            elif 8 <= data[1] <= 15:
                data = stream.flux_data_mfm(flux[data_pos-16:data_pos+16*256])
                dsum = sum(data[:-1]) & 0xff
                if dsum == data[-1]:
                    yield disk.Sector(
                        (am_data[0], 0, am_data[1]),
                        data,
                    )
                else:
                    print(
                        am_data.hex(),
                        "Z %02x" % data[1],
                        data[:21].hex(),
                        totext(data),
                        dsum == data[-1],
                    )
            else:
                print(
                    am_data.hex(),
                    "W %02x" % data[1],
                    data[:21].hex(),
                    totext(data),
                    dsum == data[-1],
                )

if __name__ == "__main__":
    main.Main(Q1MicroLite)
