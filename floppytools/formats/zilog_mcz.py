#/usr/bin/env python3

'''
   Zilog MCZ/1 8" floppies
   ~~~~~~~~~~~~~~~~~~~~~~~

   ref: 03-3018-03_ZDS_1_40_Hardware_Reference_Manual_May79.pdf
'''

import crcmod

from ..base import media
from ..base import fluxstream

crc_func = crcmod.predefined.mkCrcFun('crc-16-buypass')

class ZilogMCZ(media.Media):
    ''' ... '''

    SECTOR_SIZE = 136
    GEOMETRY = ((0, 0, 0), (77, 0, 31), SECTOR_SIZE)

    GAP = fluxstream.fm_gap(32)

    def process_stream(self, stream):
        schs = (stream.chs[0], stream.chs[1], 0)
        if not self.defined_chs(schs):
            return None

        flux = stream.fm_flux()

        retval = False
        for data_pos in stream.iter_pattern(flux, pattern=self.GAP):
            data_pos -= 4

            data = stream.flux_data_fm(flux[data_pos:data_pos+((2+self.SECTOR_SIZE)*32)])
            if data is None:
                continue

            data_crc = crc_func(data)
            if data_crc != 0:
                continue

            chs = (data[1], 0, data[0] & 0x7f)
            if not self.defined_chs(chs):
                continue

            self.did_read_sector(stream, data_pos, chs, data[:-2])
            retval = True
        return retval

ALL = [
    ZilogMCZ,
]
