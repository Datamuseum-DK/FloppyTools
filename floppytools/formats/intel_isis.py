
'''
   Decode Intel ISIS double density 8" floppies
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import crcmod

from ..base import media
from ..base import fluxstream as fs

crc_func = crcmod.predefined.mkCrcFun('xmodem')

class IntelIsis(media.Media):

    ''' Intel ISIS format 8" floppy disks '''

    SECTOR_SIZE = 128
    GEOMETRY = ((0,0,1), (76, 0, 52), SECTOR_SIZE)

    def process_stream(self, stream):
        ''' ...  '''

        if stream.chs[1] != 0:
            return None

        am_pattern =   '|-' * 16 + fs.make_mark(0x87, 0x70)
        data_pattern =   '|-' * 16 + fs.make_mark(0x85, 0x70)

        flux = stream.m2fm_flux()

        retval = False
        for am_pos in stream.iter_pattern(flux, pattern=am_pattern):

            am_flux = flux[am_pos-16:am_pos+(7*16)]
            address_mark = stream.flux_data_mfm(am_flux[1:])
            if address_mark is None:
                continue

            am_crc = crc_func(address_mark)
            if am_crc:
                continue

            chs = (address_mark[1], address_mark[2], address_mark[3])
            ms = self.sectors.get(chs)
            if ms is None:
                continue

            data_pos = flux.find(data_pattern, am_pos + 200)
            if data_pos < 0:
                continue
            if data_pos > am_pos + 1000:
                continue

            data_pos += len(data_pattern)
            data_pos -= 16

            #print(flux[data_pos-100:data_pos+16])
            data_flux = flux[data_pos:data_pos+(132*16)]
            data = stream.flux_data_mfm(data_flux[1:])
            if data is None:
                continue

            data_crc = crc_func(data[:131])
            if data_crc:
                continue

            self.did_read_sector(chs, data[1:self.SECTOR_SIZE+1], stream)
            retval = True
        return retval

ALL = [
    IntelIsis,
]
