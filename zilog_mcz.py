#/usr/bin/env python3

'''
   Zilog MCZ/1 8" floppies
   ~~~~~~~~~~~~~~~~~~~~~~~

   ref: 03-3018-03_ZDS_1_40_Hardware_Reference_Manual_May79.pdf
'''

import crcmod

import main
import disk
import fluxstream

crc_func = crcmod.predefined.mkCrcFun('crc-16-buypass')

class ZilogMCZ(disk.DiskFormat):

    FIRST_CHS = (0, 0, 0)
    LAST_CHS = (77, 0, 31)
    SECTOR_SIZE = 136

    GAP = fluxstream.fm_gap(32)

    def process(self, stream):

        if not self.validate_chs(stream.chs, none_ok=True):
            print("Ignoring", stream)
            return

        flux = stream.fm_flux()

        for data_pos in stream.iter_pattern(flux, pattern=self.GAP):
            data_pos -= 4

            data = stream.flux_data_fm(flux[data_pos:data_pos+((2+self.SECTOR_SIZE)*32)])
            if data is None:
                continue

            data_crc = crc_func(data)
            if data_crc != 0:
                continue

            chs = self.validate_chs((data[1], 0, data[0] & 0x7f))
            if not chs:
                continue

            yield disk.Sector(
                chs,
                data[:-2],
            )

if __name__ == "__main__":
    main.Main(ZilogMCZ)
