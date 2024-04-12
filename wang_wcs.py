#!/usr/bin/env python3

'''
   WANG WCS 8" floppy disks
   ~~~~~~~~~~~~~~~~~~~~~~~~

   742-0652_928_Sys-10-20-30_Vol3_Theory_Of_Operation_19840817.pdf (page 73)

'''

import crcmod

import main
import disk
import fluxstream

crc_func = crcmod.predefined.mkCrcFun('crc-16-buypass')

AM_MARK = '--|-' * 32 + '|-' * 3
DATA_MARK = '--|-' * 24 + '|-' * 3

class WangWcs(disk.DiskFormat):

    ''' WANG WCS format 8" floppy disks '''

    FIRST_CHS = (0, 0, 0)
    LAST_CHS = (76, 0, 15)
    SECTOR_SIZE = 256

    def process(self, stream):

        if not self.validate_chs(stream.chs, none_ok=True):
            print("Ignoring", stream)
            return

        flux = stream.fm_flux()

        for am_pos in stream.iter_pattern(flux, pattern=AM_MARK):

            address_mark = stream.flux_data_fm(flux[am_pos:am_pos+6*32])
            if address_mark is None:
                continue
            if max(address_mark[2:]):
                continue
            chs = self.validate_chs((address_mark[0], 0, address_mark[1]))
            if not chs:
                continue

            data_pos = flux.find(DATA_MARK, am_pos + 500)
            if data_pos < 0 or am_pos + 800 < data_pos:
                continue
            data_pos += len(DATA_MARK)

            data = stream.flux_data_fm(flux[data_pos:data_pos+((2+self.SECTOR_SIZE)*32)])
            if data is None:
                continue

            data_crc = crc_func(b'\x03' + data)
            if data_crc:
                continue

            yield disk.Sector(
                chs,
                data[:self.SECTOR_SIZE],
                source=stream.filename,
            )

if __name__ == "__main__":
    main.Main(WangWcs)
