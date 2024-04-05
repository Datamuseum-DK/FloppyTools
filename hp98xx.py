#/usr/bin/env python3

'''
   HP98xx M2MFM mode
   ~~~~~~~~~~~~~~~~~
'''

import crcmod

import main
import disk
import fluxstream
import rev_bits

crc_func = crcmod.predefined.mkCrcFun('crc-16-buypass')

#                                d d d d d d d d
#                               c c c c c c c c
AM = '--|-' * 10 + '-|' * 32 + '--|-|-|--|-|-|--'
DM = '--|-' * 10 + '-|' * 32 + '--|-|-|--|---|--'

crc_func = crcmod.predefined.mkCrcFun('crc-ccitt-false')

class HP9885(disk.DiskFormat):

    ''' HP9885 8" floppies for MX21 '''

    FIRST_CHS = (0, 0, 0)
    LAST_CHS = (66, 0, 29)
    SECTOR_SIZE = 256

    def process(self, stream):
        if not self.validate_chs(stream.chs, none_ok=True):
            raise disk.NotInterested()

        flux = fluxstream.ClockRecoveryM2FM().process(stream.iter_dt())
        prev = 0
        for am_pos in stream.iter_pattern(flux, pattern=AM):
            amf = flux[am_pos:am_pos + 80]
            am = stream.flux_data_mfm(amf)
            amc = crc_func(am)
            am = bytes(rev_bits.REV_BITS[x] for x in am)
            if amc:
                print("AMC", am.hex())
                continue
            data_pos = flux.find(DM, am_pos + 200, am_pos + 500)
            if data_pos < 0:
                print(
	    	    "%7d" % (am_pos - prev),
		    "%5d" % data_pos,
                    am.hex(),
                    "%04x" % amc,
		    flux[am_pos-32:am_pos + 700],
	        )
            else:
                o = len(DM) - 0
                dataf = flux[data_pos + o:data_pos + o + (256 + 2) * 16]
                data = stream.flux_data_mfm(dataf)
                datac = crc_func(data)
                data = bytes(rev_bits.REV_BITS[x] for x in data)
                if amc:
                    print("DATAC", "%04x" % datac)
                    continue
                txt = []
                for i in data:
                    if 32 <= i <= 126:
                        txt.append("%c" % i)
                    else:
                        txt.append("…")
                t2 = []
                for i in range(0, len(txt), 2):
                    t2.append(txt[i+1])
                    t2.append(txt[i])
                txt = ''.join(t2)
                if False:
                    print(
		        #"%7d" % (am_pos - prev),
		        #"%5d" % (data_pos - am_pos),
                        am.hex(),
                        "%04x" % amc,
                        dataf[:10],
                        "%04x" % datac,
		        txt
	            )

                yield disk.Sector(
                    (am[0], 0, am[1]),
                    data,
                )
            prev = am_pos

ALL = [
    HP9885,
]

if __name__ == "__main__":
    main.Main(HP9885)
